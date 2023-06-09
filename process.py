import cv2
import numpy as np
import os
from utils import *
from GradedAnswerSheet import *
import imutils
from imutils.perspective import four_point_transform
from imutils import contours
from constants import *

def getAnswerList(answerArea):
    imgWarpgray = cv2.cvtColor(answerArea, cv2.COLOR_BGR2GRAY)

    thresh = cv2.threshold(imgWarpgray, 0, 255,
                           cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    # cv2.imshow("col", thresh)
    # cv2.waitKey(0)
    answerList = []
    answerColumns = extractAnswerColumns(thresh)
    for columnIndex, column in enumerate(answerColumns):
        questionCnts = getBubbles(column)
        questionCnts = imutils.contours.sort_contours(questionCnts, method="top-to-bottom")[0]

        # cv2.drawContours(column, questionCnts, -1, (0, 255, 0)[::-1], 10)
        # cv2.imshow("col", column)
        # cv2.waitKey(0)
        for (q, i) in enumerate(np.arange(0, len(questionCnts), 4)):
            cnts = contours.sort_contours(questionCnts[i:i + 4])[0]
            bubbled = None
            numOfBubbled = 0
            for j, c in enumerate(cnts):
                # construct a mask that reveals only the current
                # "bubble" for the question
                mask = np.zeros(column.shape, dtype="uint8")
                cv2.drawContours(mask, [c], -1, 255, -1)

                # apply the mask to the thresholded image, then
                # count the number of non-zero pixels in the
                # bubble area
                mask = cv2.bitwise_and(column, column, mask=mask)
                # cv2.imshow("mask", mask)
                # cv2.waitKey(0)
                total = cv2.countNonZero(mask)
                # if the current total has a larger number of total
                # non-zero pixels, then we are examining the currently
                # bubbled-in answer
                # print(total)
                if bubbled is None or total > bubbled[0]:
                    bubbled = (total, j)
                if total > FILLED_THRESHOLD:
                    numOfBubbled += 1
            if bubbled[0] < FILLED_THRESHOLD or numOfBubbled > 1:
                answerList.append(-1)
            else:
                answerList.append(bubbled[1])
    
    return answerList

def scan_answer_sheet(img):
    # prep
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 0)
    imgCanny = cv2.Canny(imgBlur, 75, 200)
    kernel = np.ones((5,5),np.uint8)
    imgCanny = cv2.dilate(imgCanny,kernel,iterations = 1)
    # find sheet's contour
    contours, hierarchy = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    sheetCnt = None
    
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02*peri, True)
    
        if len(approx) == 4:
            sheetCnt = approx
            break
    
    # apply perspective transform
    scannedSheet = four_point_transform(img, sheetCnt.reshape(4, 2))
    scannedSheet = cv2.resize(scannedSheet, (WIDTH, HEIGHT))
    # testing the output, MUST COMMENT IN FINAL
    # imgArray = [img, imgCanny, scannedSheet]
    # # imgArray = [img, scannedSheet]
    # imgStack = stackImages(0.3, imgArray)
    # cv2.imshow("warp", imgStack)
    # cv2.waitKey(0)
    border_pixels = 10

    # Crop the image
    scannedSheet = scannedSheet[border_pixels:HEIGHT-border_pixels, border_pixels:WIDTH-border_pixels]

    return scannedSheet


def getTestCode(answerSheetImage):
    answerSheetInfo = getAnswerSheetInfo(answerSheetImage)
    testCodeArea= answerSheetInfo["testCode"]
    
    # Threshold
    imgWarpgray = cv2.cvtColor(testCodeArea, cv2.COLOR_BGR2GRAY)

    thresh = cv2.threshold(imgWarpgray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    threshH, threshW = thresh.shape[:2]
    crop_width = int(0.25 * threshW)
    crop_height = int(0.1 * threshH)

    cropped_thresh = thresh[crop_height:, crop_width:]
    # imgArray = [testCodeArea]
    # # imgArray = [img, scannedSheet]
    # imgStack = stackImages(0.3, imgArray)
    # cv2.imshow("warp", imgStack)
    # cv2.waitKey(0)
    testCode = ""
    questionCnts = getBubbles(cropped_thresh)
    cv2.drawContours(cropped_thresh, questionCnts, -1, (0, 255, 0)[::-1], 10)

    questionCnts = imutils.contours.sort_contours(questionCnts, method="left-to-right")[0]

    for (q, i) in enumerate(np.arange(0, len(questionCnts), 10)):

        cnts = contours.sort_contours(questionCnts[i:i + 10], method="top-to-bottom")[0]
        bubbled = None
        numOfBubbled = 0
        for j, c in enumerate(cnts):
            mask = np.zeros(cropped_thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [c], -1, 255, -1)
    
            mask = cv2.bitwise_and(cropped_thresh, cropped_thresh, mask=mask)

            total = cv2.countNonZero(mask)

            if bubbled is None or total > bubbled[0]:
                bubbled = (total, j)
            if total > FILLED_THRESHOLD_2:
                numOfBubbled += 1
        if bubbled[0] < FILLED_THRESHOLD_2 or numOfBubbled > 1:
            print("INVALID TEST CODE FILLED")
            return None
        else:
            testCode += str(bubbled[1])
    return testCode

def getCandidateNumber(answerSheetImage):
    answerSheetInfo = getAnswerSheetInfo(answerSheetImage)
    # print(answerSheetInfo)
    candidateNumberArea= answerSheetInfo["candidateNumber"]
    imgWarpgray = cv2.cvtColor(candidateNumberArea, cv2.COLOR_BGR2GRAY)
    # cv2.imshow("SBD", answerSheetInfo["infoImage"])
    cv2.waitKey(0)
    thresh = cv2.threshold(imgWarpgray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    threshH, threshW = thresh.shape[:2]
    crop_width = int(0.825 * threshW)
    crop_height = int(0.1 * threshH)
    cropped_thresh = thresh[crop_height:threshH-crop_height, threshW - crop_width:]
    # showImage("SBD", cropped_thresh, 0.6)
    
    candidateNumber = ""
    questionCnts = getBubbles(cropped_thresh)
    cv2.drawContours(cropped_thresh, questionCnts, -1, (0, 255, 0)[::-1], 10)
    questionCnts = imutils.contours.sort_contours(questionCnts, method="left-to-right")[0]

    for (q, i) in enumerate(np.arange(0, len(questionCnts), 10)):

        cnts = contours.sort_contours(questionCnts[i:i + 10], method="top-to-bottom")[0]
        bubbled = None
        numOfBubbled = 0
        for j, c in enumerate(cnts):
            mask = np.zeros(cropped_thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [c], -1, 255, -1)
            mask = cv2.bitwise_and(cropped_thresh, cropped_thresh, mask=mask)
            total = cv2.countNonZero(mask)

            if bubbled is None or total > bubbled[0]:
                bubbled = (total, j)
            if total > FILLED_THRESHOLD_2:
                numOfBubbled += 1

        if bubbled[0] < FILLED_THRESHOLD_2 or numOfBubbled > 1:
            print("INVALID CANDIDATE NUMBER FILLED")
            return None
        else:
            candidateNumber += str(bubbled[1])

    return candidateNumber

def calculateGrade(answerList, answerKeys, testCode):
    if testCode == "NA" or testCode not in answerKeys:
        print("INVALID TEST CODE, CANNOT GRADE SHEET")
        return [0, answerKeys, answerKeys]
    else:
        correctAnswerList = []
        wrongAnswerList = []
        for index, key in enumerate(answerKeys[testCode]):
            # if answerList[index] == -1:
            #     wrongAnswerList.append(index)
            if answerList[index] == key:
                correctAnswerList.append(index)
            else:
                wrongAnswerList.append(index)
        grade = round((len(correctAnswerList) / float(len(answerKeys[testCode]))) * 10, 2)
        gradeInfo = [grade, correctAnswerList, wrongAnswerList]
        return gradeInfo

def getAnswerArea(img):
    imgContours = img.copy()
    imgRectCon = img.copy()
    imgSelectedCon = img.copy()
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
    imgCanny = cv2.Canny(imgBlur, 20, 50)
    kernel = np.ones((5,5),np.uint8)
    imgCanny = cv2.dilate(imgCanny,kernel,iterations = 1)
    # imgArray = [img, imgCanny]
    # # imgArray = [img, scannedSheet]
    # imgStack = stackImages(0.3, imgArray)
    # cv2.imshow("warp", imgStack)
    # cv2.waitKey(0)
    # Finding all contours
    contours1, hierarchy = cv2.findContours(imgCanny, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    imgContours = cv2.drawContours(imgContours, contours1, -1, (0, 255, 0)[::-1], 5)
    # showImage("Answer Area 1", imgContours, 0.3)
    # Find rects
    rectCon = rectContour(contours1, 1000, 0.01)
    answerAreaCorners = getCornerPoints(rectCon[1])

    cv2.drawContours(imgSelectedCon, answerAreaCorners, -1, (0, 255, 0)[::-1], 30)
    # showImage("Answer Area 2", imgSelectedCon, 0.3)
    imgWarpColored = four_point_transform(img, answerAreaCorners.reshape(4, 2))

    # imgArray = [imgContours, imgSelectedCon, imgWarpColored]
    # imgStack = stackImages(0.3, imgArray)
    # cv2.imshow("stacked image", imgStack)
    # cv2.waitKey(0)
    # showImage("Answer Area chuan", answerAreaCorners, 0.6)

    return imgWarpColored

def getResult(answerArea, answerKeys, testCode, answerList, grade ,img):
    checkBlankAnswerList = False
    countBlankAnswer = 0
    for answer in answerList:
        if answer == -1:
            countBlankAnswer += 1
    if countBlankAnswer == len(answerList):
        checkBlankAnswerList = True
    if testCode != "NA" and checkBlankAnswerList==False:
        count = 0
        #Find answer area and store its location
        location_info = []
        answerColumns = extractAnswerColumns(answerArea)
        for columnIndex, column in enumerate(answerColumns):
            w = column.shape[1]
            h = column.shape[0]
            res = cv2.matchTemplate(img, column, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            top_left = max_loc
            location_info.append([top_left[1], top_left[1] + h, top_left[0], top_left[0] + w])
            # print(location_info[columnIndex])

        imgWarpgray = cv2.cvtColor(answerArea, cv2.COLOR_BGR2GRAY)

        thresh = cv2.threshold(imgWarpgray, 0, 255,
                            cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        answerColumns = extractAnswerColumns(thresh)
        for columnIndex, column in enumerate(answerColumns):
            cnts = cv2.findContours(column, cv2.RETR_LIST,
                                    cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)
            questionCnts = []
            for c in cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                ar = w / float(h)

                if w >= 20 and h >= 20  and ar >= 0.7 and ar <= 1.3:
                    # Check if the contour overlaps with any existing contour
                    is_overlapping = False
                    (curr_x, curr_y), curr_radius = cv2.minEnclosingCircle(c)
                    for existingCnt in questionCnts:
                        (existing_x, existing_y), existing_radius = cv2.minEnclosingCircle(existingCnt)
                        distance = np.sqrt((existing_x - curr_x)**2 + (existing_y - curr_y)**2)
                        if distance < (existing_radius + curr_radius):
                            is_overlapping = True
                            break

                    # If the contour is not overlapping with any existing contour, add it to questionCnts
                    if not is_overlapping:
                        questionCnts.append(c)
                        
            questionCnts = imutils.contours.sort_contours(questionCnts, method="top-to-bottom")[0]

            #Fill answers with color
            #Green: Key answer
            #Red: False answer
            #Blue: No answer
            for (q, i) in enumerate(np.arange(0, len(questionCnts), 4)):
                cnts = contours.sort_contours(questionCnts[i:i + 4])[0]
                cv2.drawContours(img[location_info[columnIndex][0]:location_info[columnIndex][1], location_info[columnIndex][2]:location_info[columnIndex][3]], 
                                cnts, answerKeys[testCode][count], color=(50, 193, 99), thickness=cv2.FILLED)
                if (answerList[count] != answerKeys[testCode][count] and answerList[count] != -1):
                    cv2.drawContours(img[location_info[columnIndex][0]:location_info[columnIndex][1], location_info[columnIndex][2]:location_info[columnIndex][3]], 
                                cnts, answerList[count], color=(80,127,255), thickness=cv2.FILLED)
                elif (answerList[count] == -1):
                    cv2.drawContours(img[location_info[columnIndex][0]:location_info[columnIndex][1], location_info[columnIndex][2]:location_info[columnIndex][3]], 
                                cnts, answerKeys[testCode][count], color=(208,224,64), thickness=cv2.FILLED)
                count += 1

    cv2.putText(img[SCORE_Y + round(SCORE_H/12):SCORE_Y+SCORE_H, SCORE_X:SCORE_X+SCORE_W], str(grade), (50,100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
    # cv2.imshow("filled", img)
    # cv2.waitKey()
    return img

def process(img, answerKeys, gradedAnswerSheets):
    img = scan_answer_sheet(img)
    answerArea = getAnswerArea(img)
    answerList = getAnswerList(answerArea)
    print("Answer list: ", len(answerList))
    print("Answer list: ", answerList)
    candidateNumber = getCandidateNumber(img)
    testCode = getTestCode(img)
    if candidateNumber is None:
        candidateNumber = "NA"
    if testCode is None or testCode not in answerKeys:
        testCode = "NA"
    
    gradeInfo = calculateGrade(answerList, answerKeys, testCode)
    grade = gradeInfo[0]
    correctAnswerList = gradeInfo[1]
    wrongAnswerList = gradeInfo[2]

    print("Candidate number: " + str(candidateNumber))
    print("Test code: " + str(testCode))
    print("Grade: " + str(grade))
    

    resultImage = getResult(answerArea, answerKeys, testCode, answerList, grade, img.copy())

    # Create new object of class GradedAnswerSheet having the above info
    gradedAnswerSheet = GradedAnswerSheet(candidateNumber, testCode, grade, resultImage, answerList, wrongAnswerList, correctAnswerList)
    gradedAnswerSheets.append(gradedAnswerSheet)
    
