from transformers import AutoConfig, AutoModel

# Nombre del modelo en Hugging Face
model_name = "coqui/XTTS-v2"

# Descarga la configuración del modelo
config = AutoConfig.from_pretrained(model_name)
config.save_pretrained("model/")  # Guarda en la carpeta model/

# Descarga el modelo preentrenado
model = AutoModel.from_pretrained(model_name)
model.save_pretrained("model/")  # Guarda en la carpeta model/
