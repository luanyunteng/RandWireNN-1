import os
import tqdm
import torch
import torch.nn as nn
import torch.nn.functional as F
import argparse
import torchvision.transforms as transforms
from torchvision import datasets

from model.model import RandWire
from utils.hparams import HParam
from utils.graph_reader import read_graph
from dataset.dataloader import create_dataloader, MNIST_dataloader, CIFAR10_dataloader


def validate(model, valset):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for idx, (data, target) in tqdm.tqdm(enumerate(valset)):
            data, target = data.cuda(), target.cuda()
            output = model(data)
            test_loss += F.nll_loss(output, target).item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(valset.dataset)
    accuracy = correct / len(valset.dataset)

    return test_loss, accuracy


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, required=True,
                        help="yaml file for configuration")
    parser.add_argument('-p', '--checkpoint_path', type=str, default=None, required=False,
                        help="path of checkpoint pt file")
    args = parser.parse_args()

    hp = HParam(args.config)
    graphs = [
        read_graph(hp.model.graph0),
        read_graph(hp.model.graph1),
        read_graph(hp.model.graph2),
    ]
    print('Loading model from checkpoint...')
    model = RandWire(hp, graphs).cuda()
    checkpoint = torch.load(args.checkpoint_path)
    model.load_state_dict(checkpoint['model'])
    step = checkpoint['step']

    dataset = hp.data.type
    switcher = {
            'MNIST': MNIST_dataloader,
            'CIFAR10':CIFAR10_dataloader,
            'ImageNet':create_dataloader,
            }
    assert dataset in switcher.keys(), 'Dataset type currently not supported'
    dl_func = switcher[dataset]
    valset = dl_func(hp, args, False)

    print('Validating...')
    test_avg_loss, accuracy = validate(model, valset)

    print('Result on step %d:' % step)
    print('Average test loss: %.4f' % test_avg_loss)
    print('Accuracy: %.3f' % accuracy)
