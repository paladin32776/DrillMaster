import cv2
import numpy as np
import scipy.signal

def processPCBimage(im, minsize=30, threshold=50):
    height, width, channels = im.shape

    imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(imgray, threshold, 255, 0)
    im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Remove contours too small:
    ind = list()
    for n, c in enumerate(contours):
        x, y, w, h = cv2.boundingRect(c)
        if (w < minsize or h < minsize):
            # cv2.rectangle(im, (x, y), (x + w, y + h), (0, 0, 255), 1, 1)
            ind.append(n)
    contours = [i for j, i in enumerate(contours) if j not in ind]

    im_out = np.zeros((height, width, 3), np.uint8)
    cv2.drawContours(im_out, contours, -1, (255, 255, 255), -1)
    cv2.bitwise_not(im_out, im_out)

    imgray = cv2.cvtColor(im_out, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(imgray, 50, 255, 0)
    im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Remove contours too small:
    ind = list()
    for n, c in enumerate(contours):
        x, y, w, h = cv2.boundingRect(c)
        if (w < 30 or h < 30):
            # cv2.rectangle(im, (x, y), (x + w, y + h), (0, 255, 255), 1, 1)
            ind.append(n)
    contours = [i for j, i in enumerate(contours) if j not in ind]

    im_out = np.zeros((height, width, 3), np.uint8)
    cv2.drawContours(im_out, contours, -1, (255, 255, 255), -1)
    cv2.bitwise_not(im_out, im_out)

    return im_out


def cross_image(im1, im2):
   # get rid of the color channels by performing a grayscale transform
   # the type cast into 'float' is to avoid overflows
   im1_gray = np.sum(im1.astype('float'), axis=2)
   im2_gray = np.sum(im2.astype('float'), axis=2)

   # get rid of the averages, otherwise the results are not good
   im1_gray -= np.mean(im1_gray)
   im2_gray -= np.mean(im2_gray)

   # calculate the correlation image; note the flipping of onw of the images
   return scipy.signal.fftconvolve(im1_gray, im2_gray[::-1,::-1], mode='same')