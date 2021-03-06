# Usage : Détection du port du masque en vidéo stream
# python3 detect_mask_video.py

# packages
import numpy as np
import argparse
import imutils
import time
import cv2
import os
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream

def detect_and_predict_mask(frame, faceNet, maskNet):
	# grab the dimensions of the frame and then construct a blob from it
	(h, w) = frame.shape[:2]
	blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
		(104.0, 177.0, 123.0))

	# pass the blob through the network and obtain the face detections
	faceNet.setInput(blob)
	detections = faceNet.forward()
	
	# initialize our list of faces, their corresponding locations,and the list of predictions from our face mask network
	faces = []
	locs = []
	preds = []

	# Boucle sur les detections
	for i in range(0, detections.shape[2]):
		# extraction de la probabilité associée à la  detection
		confidence = detections[0, 0, i, 2]

		# filtre des probabilités faibles en dessous d'un certain seuil minimal
		if confidence > args["confidence"]:
			# compute the (x, y)-coordinates of the bounding box for the object
			box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
			(startX, startY, endX, endY) = box.astype("int")
			(startX, startY) = (max(0, startX), max(0, startY))
			(endX, endY) = (min(w - 1, endX), min(h - 1, endY))
			face = frame[startY:endY, startX:endX]
			face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
			face = cv2.resize(face, (224, 224))
			face = img_to_array(face)
			face = preprocess_input(face)
			faces.append(face)
			locs.append((startX, startY, endX, endY))

	# Prédictions que si au moins une personne est detecté
	if len(faces) > 0:
		faces = np.array(faces, dtype="float32")
		preds = maskNet.predict(faces, batch_size=32)

	# return les prédictions de port du masque avec leur localisations correspondantes
	return (locs, preds)

# construction du parser d'argument
ap = argparse.ArgumentParser()
ap.add_argument("-f", "--face", type=str,
	default="face_detector",
	help="path to face detector model directory")
ap.add_argument("-m", "--model", type=str,
	default="mask_detector.model",
	help="path to trained face mask detector model")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

# load our serialized face detector model from disk
print("[INFO] Chargement du modèle de détection de port du masque...")
prototxtPath = os.path.sep.join([args["face"], "deploy.prototxt"])
weightsPath = os.path.sep.join([args["face"],
	"res10_300x300_ssd_iter_140000.caffemodel"])
faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)
maskNet = load_model(args["model"])

# initialise la video stream 
print("[INFO] Début du Stream Vidéo...")
vs = VideoStream(src=0).start()
time.sleep(2.0)

# loop over the frames from the video stream
while True:
	# grab the frame from the threaded video stream and et la redimensionne pour avoir une largeur max de 1200 pixels
	frame = vs.read()
	frame = imutils.resize(frame, width=1500)

	# detecte les visages dans la fenêtre et determine s'ils portent un masque ou non
	(locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)

	# boucle sur les visages détectés et leurs emplacements 
	for (box, pred) in zip(locs, preds):
		(startX, startY, endX, endY) = box
		(mask, withoutMask) = pred

		# determine la classe du  label et sa couleur utilisée pour tracer le rectangle et écrire la probabilité
		label = "Masque" if mask > withoutMask else "pas de  Masque"
		color = (0, 255, 0) if label == "Masque" else (0, 0, 255)
			
		# Ajoute la probabilité au label
		label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

		# Affichage du label et de la bounding box rectangle sur la fenêtre
		cv2.putText(frame, label, (startX, startY - 10),
			cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
		cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

	# show the output frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF

	# 'appuyer sur la touche 'q' du clavier pour arrêter le stream et l'execution du programme
	if key == ord("q"):
		break

# cleanup
cv2.destroyAllWindows()
vs.stop()
