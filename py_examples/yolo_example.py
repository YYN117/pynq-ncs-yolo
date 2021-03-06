"""
Example usage on the PYNQ-Z1:

python3.6 yolo_example.py ../graph ../images/dog.jpg ../images/dog-output.jpg
"""

from mvnc import mvncapi as mvnc
import sys,os,time,csv,getopt,cv2
import numpy as np
from datetime import datetime
import PIL.Image

classes = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train","tvmonitor"]
class_colors = [(255,102,102),
                (255,178,102),
                (255,255,102),
                (178,255,102),
                (102,255,102),
                (102,255,178),
                (102,255,255),
                (102,178,255),
                (102,102,255),
                (178,102,255),
                (255,102,255),
                (255,102,178),
                (192,192,192),
                (96,96,96   ),
                (204,0,0    ),
                (204,102,0  ),
                (153,153,0  ),
                (76,153,0   ),
                (0,153,153  ),
                (255,255,204)]

def interpret_output(output, img_width, img_height):
    w_img = img_width
    h_img = img_height
    print ((w_img, h_img))
    threshold = 0.2
    iou_threshold = 0.5
    num_class = 20
    num_box = 2
    grid_size = 7
    probs = np.zeros((7,7,2,20))
    class_probs = (np.reshape(output[0:980],(7,7,20)))#.copy()
    #print(class_probs)
    scales = (np.reshape(output[980:1078],(7,7,2)))#.copy()
    #print(scales)
    boxes = (np.reshape(output[1078:],(7,7,2,4)))#.copy()
    offset = np.transpose(np.reshape(np.array([np.arange(7)]*14),(2,7,7)),(1,2,0))
    #boxes.setflags(write=1)
    boxes[:,:,:,0] += offset
    boxes[:,:,:,1] += np.transpose(offset,(1,0,2))
    boxes[:,:,:,0:2] = boxes[:,:,:,0:2] / 7.0
    boxes[:,:,:,2] = np.multiply(boxes[:,:,:,2],boxes[:,:,:,2])
    boxes[:,:,:,3] = np.multiply(boxes[:,:,:,3],boxes[:,:,:,3])

    boxes[:,:,:,0] *= w_img
    boxes[:,:,:,1] *= h_img
    boxes[:,:,:,2] *= w_img
    boxes[:,:,:,3] *= h_img

    for i in range(2):
        for j in range(20):
            probs[:,:,i,j] = np.multiply(class_probs[:,:,j],scales[:,:,i])
    #print (probs)
    filter_mat_probs = np.array(probs>=threshold,dtype='bool')
    filter_mat_boxes = np.nonzero(filter_mat_probs)
    boxes_filtered = boxes[filter_mat_boxes[0],filter_mat_boxes[1],filter_mat_boxes[2]]
    probs_filtered = probs[filter_mat_probs]
    classes_num_filtered = np.argmax(probs,axis=3)[filter_mat_boxes[0],filter_mat_boxes[1],filter_mat_boxes[2]]

    argsort = np.array(np.argsort(probs_filtered))[::-1]
    boxes_filtered = boxes_filtered[argsort]
    probs_filtered = probs_filtered[argsort]
    classes_num_filtered = classes_num_filtered[argsort]

    for i in range(len(boxes_filtered)):
        if probs_filtered[i] == 0 : continue
        for j in range(i+1,len(boxes_filtered)):
            if iou(boxes_filtered[i],boxes_filtered[j]) > iou_threshold :
                probs_filtered[j] = 0.0

    filter_iou = np.array(probs_filtered>0.0,dtype='bool')
    boxes_filtered = boxes_filtered[filter_iou]
    probs_filtered = probs_filtered[filter_iou]
    classes_num_filtered = classes_num_filtered[filter_iou]

    result = []
    for i in range(len(boxes_filtered)):
        result.append([classes_num_filtered[i],boxes_filtered[i][0],boxes_filtered[i][1],boxes_filtered[i][2],boxes_filtered[i][3],probs_filtered[i]])

    return result

def iou(box1,box2):
    tb = min(box1[0]+0.5*box1[2],box2[0]+0.5*box2[2])-max(box1[0]-0.5*box1[2],box2[0]-0.5*box2[2])
    lr = min(box1[1]+0.5*box1[3],box2[1]+0.5*box2[3])-max(box1[1]-0.5*box1[3],box2[1]-0.5*box2[3])
    if tb < 0 or lr < 0 : intersection = 0
    else : intersection =  tb*lr
    return intersection / (box1[2]*box1[3] + box2[2]*box2[3] - intersection)


def draw_boxes(img, results, img_width, img_height):
    img_cp = img.copy()
    disp_console = True
    #if self.filewrite_txt :
    #ftxt = open(self.tofile_txt,'w')
    for i in range(len(results)):
        x = int(results[i][1])
        y = int(results[i][2])
        w = int(results[i][3])//2
        h = int(results[i][4])//2
        if disp_console : print ('    class : ' + classes[results[i][0]] + ' , [x,y,w,h]=[' + str(x) + ',' + str(y) + ',' + str(int(results[i][3])) + ',' + str(int(results[i][4]))+'], Confidence = ' + str(results[i][5]) )
        xmin = x-w
        xmax = x+w
        ymin = y-h
        ymax = y+h
        if xmin<0:
            xmin = 0
        if ymin<0:
            ymin = 0
        if xmax>img_width:
            xmax = img_width
        if ymax>img_height:
            ymax = img_height
        # Add boxes to the image
        color = class_colors[results[i][0]]
        cv2.rectangle(img_cp,(xmin,ymin),(xmax,ymax),color,2)
        cv2.rectangle(img_cp,(xmin,ymin-20),(xmax,ymin),color,-1)
        cv2.putText(img_cp,classes[results[i][0]] + ' : %.2f' % results[i][5],(xmin+5,ymin-7),cv2.FONT_HERSHEY_DUPLEX,0.5,(0,0,0),1)
    return(img_cp)

if len(sys.argv) != 4:
    print ("YOLOv1 Tiny example: python3 yolo_example.py <graph_file> <input_image> <output_image>")
    sys.exit()

network_blob=sys.argv[1]
# configuration NCS
mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)
devices = mvnc.EnumerateDevices()
if len(devices) == 0:
    print('No devices found')
    quit()
device = mvnc.Device(devices[0])
device.OpenDevice()
opt = device.GetDeviceOption(mvnc.DeviceOption.OPTIMISATION_LIST)
# load blob
with open(network_blob, mode='rb') as f:
    blob = f.read()
graph = device.AllocateGraph(blob)
graph.SetGraphOption(mvnc.GraphOption.ITERATIONS, 1)
iterations = graph.GetGraphOption(mvnc.GraphOption.ITERATIONS)
# image preprocess
dim=(448,448)
img = cv2.imread(sys.argv[2])
# Convert to RGB for the neural network and also for PIL
img = img[:,:,(2,1,0)]
# Resize to 448x448 for the neural network
im = cv2.resize(img.copy()/255.0, dsize=(448, 448), interpolation=cv2.INTER_CUBIC)
start = datetime.now()
# start MOD
graph.LoadTensor(im.astype(np.float16), 'user object')
out, userobj = graph.GetResult()
#
end = datetime.now()
elapsedTime = end-start
print ('total time is " milliseconds', elapsedTime.total_seconds()*1000)
results = interpret_output(out.astype(np.float32), img.shape[1], img.shape[0]) # fc27 instead of fc12 for yolo_small
# Draw boxes and labels on the image
img_res = draw_boxes(img, results, img.shape[1], img.shape[0])
# Save the file
# Display image in Jupyter notebook
img_out = PIL.Image.fromarray(img_res)
img_out.save(sys.argv[3])
# Close the NCS device
graph.DeallocateGraph()
device.CloseDevice()
