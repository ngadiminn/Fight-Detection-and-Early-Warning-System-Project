import torch
import torchvision
import numpy as np
import albumentations as A

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
CLASSES_LIST = ['fight', 'noFight']

def transform_():
    """Transforms untuk MViT_v2_s dengan input size 224x224"""
    transform = A.Compose([
        A.Resize(256, 256, always_apply=True),
        A.CenterCrop(224, 224, always_apply=True),
        A.Normalize(
            mean=[0.45, 0.45, 0.45],
            std=[0.225, 0.225, 0.225],
            always_apply=True
        )
    ])
    return transform

def loadModel(modelPath):
    """Memuat bobot pretrained MViT_v2_s"""
    PATH = modelPath
    model_ft = torchvision.models.video.mvit_v2_s(weights='DEFAULT')
    
    # Modifikasi classifier head untuk 2 kelas
    num_ftrs = model_ft.head[1].in_features
    model_ft.head[1] = torch.nn.Linear(num_ftrs, 2)
    
    # Load saved weights
    model_ft.load_state_dict(torch.load(PATH, map_location=torch.device(device)))
    model_ft.to(device)
    model_ft.eval()
    
    return model_ft

def PredTopKClass(k, clips, model):
    """Mengembalikan 1 nama kelas dengan probabilitas tertinggi"""
    with torch.no_grad():
        input_frames = np.array(clips)
        input_frames = np.expand_dims(input_frames, axis=0)
        input_frames = np.transpose(input_frames, (0, 4, 1, 2, 3))
        
        input_frames = torch.tensor(input_frames, dtype=torch.float32)
        input_frames = input_frames.to(device)

        outputs = model(input_frames)
        soft_max = torch.nn.Softmax(dim=1)  
        probs = soft_max(outputs.data) 
        prob, indices = torch.topk(probs, k)

    Top_k = indices[0]
    Classes_nameTop_k = [CLASSES_LIST[item].strip() for item in Top_k]
    return Classes_nameTop_k[0]

def PredTopKProb(k, clips, model):
    """Mengembalikan list berisi nama kelas dan nilai probabilitasnya"""
    with torch.no_grad():
        input_frames = np.array(clips)
        input_frames = np.expand_dims(input_frames, axis=0)
        input_frames = np.transpose(input_frames, (0, 4, 1, 2, 3))
        
        input_frames = torch.tensor(input_frames, dtype=torch.float32)
        input_frames = input_frames.to(device)

        outputs = model(input_frames)
        soft_max = torch.nn.Softmax(dim=1)  
        probs = soft_max(outputs.data) 
        prob, indices = torch.topk(probs, k)

    Top_k = indices[0]
    Classes_nameTop_k = [CLASSES_LIST[item].strip() for item in Top_k]
    ProbTop_k = prob[0].tolist()
    ProbTop_k = [round(elem, 5) for elem in ProbTop_k]
    return list(zip(Classes_nameTop_k, ProbTop_k))