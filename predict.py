import cv2
import numpy as np
from skimage.transform import resize
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras import backend as kb


def get_model(model_path):
    global model
    model = load_model(model_path)
    print(" * model loaded!")

def transform_image(image, target_size = (224, 224)):
    # image = PIL image
    image_array = np.asarray(image.convert("RGB"))
    image_array = image_array / 255.
    image_array = resize(image_array, target_size)
    return image_array

def preprocess_image(image, target_size=(224, 224)):
    # image = PIL image
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = image.resize(target_size)
    image = img_to_array(image)
    image = np.expand_dims(image, axis=0)
    return image

def get_output_layer(model, layer_name):
    layer_dict = dict([(layer.name, layer) for layer in model.layers])
    layer = layer_dict[layer_name]
    return layer


def heatmap(model, orginal_image, transformed_image, predicted_class_index):
    # build tensorflow computational graph
    class_weights = model.layers[-1].get_weights()[0]  # class_weight.shape = (1024, 14)
    final_conv_layer = get_output_layer(model, "bn")
    get_output = kb.function([model.layers[0].input], [final_conv_layer.output, model.layers[-1].output])
    [conv_outputs, predictions] = get_output([np.array([transformed_image])])
    conv_outputs = conv_outputs[0, :, :, :]  # conv_outputs:  (7, 7, 1024) and predictions: (1, 14)

    # Create the class activation map.
    cam = np.zeros(dtype=np.float32, shape=(conv_outputs.shape[:2]))
    for i, w in enumerate(class_weights[predicted_class_index]):
        cam += w * conv_outputs[:, :, i]

    # merge the original image and the class activation map
    cam /= np.max(cam)
    cam = cv2.resize(cam, orginal_image.shape[:2])
    heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
    heatmap[np.where(cam < 0.2)] = 0
    heatmap = heatmap * 0.5 + orginal_image
    heatmap = (heatmap / np.max(heatmap)) * 255  # normalizing

    cv2.imwrite("output/heatmap.jpg", heatmap)
    return heatmap

def predict(model, image, target_size=(224, 224), show_heatmap=False):
    processed_image = preprocess_image(image, target_size)
    prediction = model.predict(processed_image).tolist()
    if show_heatmap:
        original_image = np.asarray(image.convert("RGB"))
        transformed_image = transform_image(image)
        predicted_class_index = np.argmax(prediction)
        heatmap_img = heatmap(model, original_image, transformed_image, predicted_class_index)
        return (prediction, heatmap_img)
    else:
        return prediction
