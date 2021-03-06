import time
from absl import app,flags, logging
import cv2
import numpy as np
import tensorflow as tf
from yolov3_tf2.models import (
    YoloV3, YoloV3Tiny
)
from yolov3_tf2.dataset import transform_images, load_tfrecord_dataset
from yolov3_tf2.utils import draw_outputs
from flask import Flask,render_template, request, Response, jsonify, send_from_directory, abort
import os
import sys

print("sys argv is : {} ",sys.argv)
try:
  args=sys.argv.remove('--log-file=-')
except:
  args=sys.argv 

flags.FLAGS(args)


classes_path = './data/labels/coco.names'
weights_path = './weights/yolov3-tiny.tf'
tiny = True                    
size = 416                      
output_path = './static/detections/'   
num_classes = 80                
upload_path='./static/uploads/'



# load in weights and classes
physical_devices = tf.config.experimental.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

if tiny:
    yolo = YoloV3Tiny(classes=num_classes)
else:
    yolo = YoloV3(classes=num_classes)

yolo.load_weights(weights_path).expect_partial()
print('weights loaded')

class_names = [c.strip() for c in open(classes_path).readlines()]
print('classes loaded')

# Initialize Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = upload_path 

@app.route("/")
def index():
  return render_template("index.html")

@app.route("/about")
def about():
  return render_template("about.html")


@app.route('/uploader', methods= ['GET','POST'])
def get_image():
    image = request.files['file']
    image_name = image.filename
    path=os.path.join(app.config['UPLOAD_FOLDER'],image_name)
    image.save(path)
    print('input saved to:{}',path)

    img_raw = tf.image.decode_image(
        open(path, 'rb').read(), channels=3)
    img = tf.expand_dims(img_raw, 0)
    img = transform_images(img, size)

    #image2 = image
    #image2_name = image2.filename
    #image2.save(os.path.join(upload_path,image2_name))

    t1 = time.time()
    boxes, scores, classes, nums = yolo(img)
    t2 = time.time()
    print('time: {}'.format(t2 - t1))

    print('detections:')
    for i in range(nums[0]):
        print('\t{}, {}, {}'.format(class_names[int(classes[0][i])],
                                        np.array(scores[0][i]),
                                        np.array(boxes[0][i])))
    img = cv2.cvtColor(img_raw.numpy(), cv2.COLOR_RGB2BGR)
    img = draw_outputs(img, (boxes, scores, classes, nums), class_names)
    cv2.imwrite(output_path + image_name, img)
    print('output saved to: {}'.format(output_path + image_name))
    
    # prepare image for response
    _, img_encoded = cv2.imencode('.png', img)
    response = img_encoded.tostring()
    
    #remove temporary image
    os.remove(path)

    try:
        #return Response(response=response, status=200, mimetype='image/png')
        return render_template("uploaded.html", display_detection = image_name,fname = image_name)
    except FileNotFoundError:
        abort(404)

    os.remove(format(output_path + image_name))

if __name__ == '__main__':
    app.run(debug=True)