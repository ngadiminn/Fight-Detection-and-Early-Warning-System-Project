import json

notebook_path = 'Fight_Detection_MViT_Colab.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# The updated Cell 23 content
cell_23_source = [
    "# Training configuration\n",
    "NUM_EPOCHS = 50\n",
    "LEARNING_RATE = 0.0001\n",
    "WEIGHT_DECAY = 1e-3\n",
    "\n",
    "# Loss function with Label Smoothing\n",
    "criterion = nn.CrossEntropyLoss(label_smoothing=0.15)\n",
    "\n",
    "# Optimizer with Weight Decay (AdamW)\n",
    "optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)\n",
    "\n",
    "# Learning rate scheduler (CosineAnnealing for smooth decay)\n",
    "scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(\n",
    "    optimizer,\n",
    "    T_0=10,\n",
    "    T_mult=2,\n",
    "    eta_min=1e-6\n",
    ")\n",
    "\n",
    "print(\"=\"*80)\n",
    "print(\"⚙️ TRAINING CONFIGURATION\")\n",
    "print(\"=\"*80)\n",
    "print(f\"Number of epochs: {NUM_EPOCHS}\")\n",
    "print(f\"Learning rate: {LEARNING_RATE}\")\n",
    "print(f\"Weight Decay: {WEIGHT_DECAY}\")\n",
    "print(f\"Batch size: {BATCH_SIZE}\")\n",
    "print(f\"Optimizer: AdamW\")\n",
    "print(f\"Loss function: CrossEntropyLoss (Label Smoothing=0.15)\")\n",
    "print(f\"LR Scheduler: CosineAnnealingWarmRestarts\")\n",
    "print(\"=\"*80)\n"
]

# We need to find the correct cells. 
# Previously they were Cell 23 and Cell 25, but finding them dynamically is safer.
for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = "".join(cell.get('source', []))
        
        # Identify the hyperparameter configuration cell
        if "NUM_EPOCHS = 30" in source and "optimizer = torch.optim.Adam" in source:
            cell['source'] = cell_23_source
            print("Successfully updated hyperparameter cell.")
            
        # Identify the training loop cell
        if "def train_model_colab(" in source and "scheduler.step(epoch_acc)" in source:
            # Replace the specific scheduler step lines
            new_source = source.replace(
                "            if phase == 'val':\n                scheduler.step(epoch_acc)",
                "            if phase == 'val':\n                if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):\n                    scheduler.step(epoch_acc)\n                else:\n                    scheduler.step()"
            )
            cell['source'] = [line + ('\n' if i < len(new_source.split('\n')) - 1 else '') for i, line in enumerate(new_source.split('\n'))]
            print("Successfully updated training loop cell.")

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Notebook saved successfully!")
