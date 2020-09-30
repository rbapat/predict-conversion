from torch.utils.data import DataLoader
import torch.optim as optim
import multiprocessing
import torch.nn as nn
import torch
import shutil
import os

from research.util.Grapher import TrainGrapher
from research.datasets.classification_dataset import DataParser
#from research.datasets.freesurfer_dataset import DataParser

from research.models.inception import InceptionModel
from research.models.experimental import EModel
from research.models.svoxnet import SVoxNet
from research.models.densenet import DenseNet

# model hyperparameters
LEARNING_RATE = 0.001
MOMENTUM = 0.9
WEIGHT_DECAY = 0
NUM_EPOCHS = 1000
BATCH_SIZE = 5

# weight/graphing parameters
LOAD_WEIGHT = False
SAVE_FREQ = 10
SAVE_MODEL = True
GRAPH_FREQ = 1
GRAPH_METRICS = True
SAVE_THRESH = 90

# data shapes
DATA_DIM = (128, 128, 128)
NUM_OUTPUTS = 2

def main():
    csv_path = os.path.join(os.getcwd(), "adni_test_data.csv")
    dataset = DataParser(csv_path, DATA_DIM, NUM_OUTPUTS, splits = [0.8, 0.2])
    #dataset = DataParser(DATA_DIM, NUM_OUTPUTS, splits = [0.8, 0.2])

    # initialize the data loaders needed for training and validation
    train_loader = DataLoader(dataset.get_loader(0), batch_size = BATCH_SIZE, shuffle = True)
    val_loader = DataLoader(dataset.get_loader(1), batch_size = BATCH_SIZE, shuffle = True)
    #test_loader = DataLoader(dataset.get_loader(2), batch_size = BATCH_SIZE, shuffle = True)
    loaders = [train_loader, val_loader]#, test_loader]

    # initialize matplotlib graph and get references to lists to be graphed
    grapher = TrainGrapher(GRAPH_METRICS, "Accuracy", "Loss")
    accuracy = grapher.add_lines("Accuracy", 'lower left', "Train Accuracy", "Validation Accuracy")
    losses = grapher.add_lines("Loss", 'upper right', "Train Loss", "Validation Loss")

    # initialize model, loss function, and optimizer
    model = DenseNet(*DATA_DIM, NUM_OUTPUTS).cuda()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr = LEARNING_RATE, weight_decay = WEIGHT_DECAY, momentum = MOMENTUM)

    # load the model weights from disk if it exists
    if LOAD_WEIGHT and os.path.exists('optimal.t7'):
        ckpt = torch.load('optimal.t7')
        model.load_state_dict(ckpt['state_dict'])
        optimizer.load_state_dict(ckpt['optimizer'])
        print("Loaded Optimal Weights")

    # load weights from this model to only the first few layers
    if os.path.exists('pretrain.t7') and model.identifier == 'Pretrain':
        #state_dict = torch.load('pretrain.t7')['state_dict']
        with torch.no_grad():
            ckpt = torch.load('pretrain.t7')
            for name, param in ckpt['state_dict'].items():
                if name not in model.state_dict() or model.state_dict()[name].shape != param.shape:
                    continue

                model.state_dict()[name].copy_(param)
                #model.state_dict()[name].requires_grad = False

                print("Loaded", name)

            print("Pretrained Weights Loaded!")

    if os.path.exists('autoencoder.t7') and model.identifier =='PretrainStem':
        model.pretrain_stem()

    # if checkpoint directory doesnt exist, create one if needed
    if SAVE_MODEL and not os.path.exists('checkpoints'):
        os.mkdir('checkpoints')

    # run main training loop. Validation set is tested after every training iteration
    exit_early, stop_early = False, False
    for epoch in range(1, NUM_EPOCHS + 1):
        for phase in range(len(loaders)): # phase: 0 = train, 1 = val, 2 = test
            running_loss, running_correct = 0.0, 0.0

            # dont use test set unless we are in early stopping phase
            if not stop_early and phase == 2:
                continue

            for (data, label) in loaders[phase]:
                # convert data to cuda because model is cuda
                data, label = data.cuda(), label.type(torch.LongTensor).cuda()
                
                # eval mode changes behavior of dropout and batch norm for validation
                
                model.train(phase == 0)
                probs = model(data)

                # get class predictions
                label = torch.argmax(label, dim = 1)
                preds = torch.argmax(model.softmax(probs), dim = 1)

                loss = criterion(probs, label)

                optimizer.zero_grad()

                # backprop if in training phase
                if phase == 0:
                    loss.backward()
                    optimizer.step()

                # TODO: Loss calculation might be incorrect, check it
                running_loss += loss.item() * len(data)
                running_correct += (preds == label).sum().item()

            # get metrics over entire dataset
            true_accuracy = 100 * running_correct / len(dataset.get_loader(phase))
            true_loss = running_loss / len(dataset.get_loader(phase))

            if phase == 0:
                print("Epoch %d/%d, train accuracy: %.2f" % (epoch, NUM_EPOCHS, true_accuracy), end ="") 
            elif phase == 1:
                print(", val accuracy: %.2f, val loss: %.4f" % (true_accuracy, true_loss))
            elif phase == 2:
                print("Model stopping early with an accuracy of %.2f and a loss of %.2f" % (true_accuracy, true_loss))
                exit_early = True
                break

            if phase == 1 and true_accuracy > SAVE_THRESH:
                state = {
                    'state_dict': model.state_dict(),
                    'optimizer': optimizer.state_dict()
                }

                # save model with early_stop_ prefix if needed
                prefix = ""
                if exit_early:
                    prefix = "true_accuracy_%.2f_" % true_accuracy

                path = os.path.join('checkpoints', '%s_%sepoch_%d.t7' % (model.identifier, prefix, epoch))
                torch.save(state, path)

            # add metrics to list to be graphed
            if phase < 2:
                accuracy[phase].append(true_accuracy)
                losses[phase].append(true_loss)

        if epoch % GRAPH_FREQ == 0:
            grapher.update() 

        # output model weights to checkpoints directory if specified
        if exit_early or (SAVE_MODEL and epoch % SAVE_FREQ == 0):
            state = {
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict()
            }

            # save model with early_stop_ prefix if needed
            prefix = ""
            if exit_early:
                prefix = "early_stop_"

            path = os.path.join('checkpoints', '%s_%sepoch_%d.t7' % (model.identifier, prefix, epoch))
            torch.save(state, path)

        if exit_early:
            break

    grapher.show()

if __name__ == '__main__':
    main()

'''
ls -lR ~/Research/ADNI/Original | grep 'nii' | parallel -- jobs 8 recon-all -s {.] -i {} -autorecon1
'''
