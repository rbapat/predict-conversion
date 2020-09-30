import skimage.transform as transform
from torch.utils.data import DataLoader
from torch.utils.data import Dataset
import nibabel as nib
import pandas as pd
import numpy as np
import random
import torch
import xml.etree.ElementTree as ET
import os

from research.util.util import data_utils

# Custom implementation of PyTorch's default data loader
class TorchLoader(Dataset):
    def __init__(self, dataset, data_dim, num_output):
        self.dataset = dataset
        self.num_output = num_output
        self.data_dim = data_dim

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        data = self.dataset[idx]
        
        # scans are loaded dynamically because I cant fit the entire dataset in RAM
        mat = nib.load(data[0])
        
        mat = data_utils.crop_scan(mat.get_fdata().squeeze())
        mat = transform.resize(torch.Tensor(mat), self.data_dim)

        mat = 255 * (mat - mat.min())/(mat.max() - mat.min())

        one_hot = np.zeros(self.num_output)
        one_hot[data[1]] = 1

        return mat, one_hot

class DataParser:
    def __init__(self, data_dim, num_output, splits = [0.8, 0.2]):
        self.data_dim = data_dim
        self.num_output = num_output
        
        self.create_dataset(splits)

    def extract_cid(self, abs_path):
        root = ET.parse(abs_path).getroot()

        group = root.findall('project/subject/researchGroup')

        if len(group) != 1:
            raise Exception("Number of research group is not 1! %s" % abs_path)

        return ["CN", "AD", "MCI"].index(group[0].text)

    def assemble_xml(self, metadata_path): 
        root = ET.parse(metadata_path).getroot()    

        subject_id = root.findall('subject')[0].get('id')
        series_id = root.findall('series')[0].get('uid')
        image_id = root.findall('image')[0].get('uid')

        return 'ADNI_%s_FreeSurfer_Cross-Sectional_Processing_brainmask_%s_%s.xml' % (subject_id, series_id, image_id)

    def create_dataset(self, splits):
        dxdict = {}
        path = os.path.join('ADNI', 'FreeSurfer')
        for file in os.listdir(path):
            abs_path = os.path.join(path, file)
            if file[-3:] == 'xml' and os.path.isfile(abs_path):
                dxdict[file] = self.extract_cid(abs_path)

        dataset = []
        for (root, dirs, files) in os.walk(path):
            for idx, file in enumerate(files):
                if file[-3:] == 'nii':
                    path = os.path.join(root, file)

                    xml_file = self.assemble_xml(os.path.join(root, files[1 - idx]))
                    cid = dxdict[xml_file]

                    if cid < self.num_output:
                        dataset.append((path, cid))

        random.shuffle(dataset)

        if sum(splits) != 1.0:
            raise Exception("Dataset splits does not sum to 1")

        self.subsets = []
        minIdx, maxIdx = 0, 0

        # split the dataset into the specified chunks
        for idx, split in enumerate(splits):
            chunk = int(len(dataset) * split)
            maxIdx += chunk

            subset = dataset[minIdx:maxIdx]
            random.shuffle(subset)

            self.subsets.append(TorchLoader(subset, self.data_dim, self.num_output))

            minIdx += chunk

    def get_loader(self, idx):
        return self.subsets[idx]

    def get_set_length(self, idx):
        return len(self.subsets[idx])