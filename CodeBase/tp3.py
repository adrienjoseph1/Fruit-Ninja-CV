from cmu_112_graphics_openCV import *
from tkinter import *
import cv2
import time
import math
import random
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont

#***************************** INIT *****************************

def appStarted(app):
    app.mode = 'splashScreenMode'
    app.calFrame = None

    app.minCamThreshold = 240
    app.minContourArea = 1000
    app.calibrationArea = 1000
    app.highScore = 0
    app.highScore2 = 0

    app.gm2Countdown = 90

    app.font = 'Impact' #USE TO CHANGE FONT

    app.scaledx, app.scaledy = 540, 360 #playable area as small as possible

    resetBounds(app) #reset the bounds of the playable area
    appRestart(app)

def appRestart(app):
    app.gameOver = False
    app.score = 0
    app.scoreList = []
    app.scoreListTime = time.time()
    app.scoresTimeReset = 2 
    app.comboDispTime = time.time()

    app.lives = 3
    app.fruits = []
    app.timerDelay = 15 #around 60 frames per second
    app.startTime = time.time() #used for throwing new fruits
    app.cursor = None #where the flashlight curr is

    app.fruitDelay = 4
    
    app.sliceLine = None #slicing line
    app.sliceTime = time.time_ns() #time since last checked for slice
    app.sliceNum = 0
    app.comboNum = 0

    app.comboTime = time.time()
    app.overMessage = ''

    app.gm2Time = time.time()

    app.sliceList = []
    app.bladePoints = 3

    app.bombTime = 0

#***************************** FRUIT CODE *****************************

class Fruit(object):

    def __init__(self, name, color, coords, vx, vy, timeSinceLastSlice, pv):
        self.name = name
        self.color = color
        self.coords = coords #list of x,y points for coordinates
        self.vx, self.vy = vx, vy #horizontal and vertical velocity
        self.isSliced = False #if the fruit has already been sliced
        self.beenOnScreen = False #if the fruit has been on screen at least once
        self.x, self.y = self.coords[0], self.coords[1] #the left most point on the fruit
        self.addListX = [] 
        self.addListY = []
        self.timeSinceLastSlice = time.time() #time since fruit was last sliced
        self.pv = pv #fruit point value

    #returns polygon tuple if sliced or None if cannot be sliced
    def split(self, line):
        poly = coordsToPoly(self.coords)
        modPoly = findPolyLineIntersections(poly, line)
        polygonTuple = slicePolygon(modPoly)
        return polygonTuple
    
    #get the area of a polygon
    #area formula https://www.mathopenref.com/coordpolygonarea.html
    def getArea(self):
        coords = self.coords + [self.coords[0],self.coords[1]]
        coords = coordsToPoly(coords)
        sum = 0
        for i in range(len(coords)-1):
            sum += (coords[i][0]*coords[i+1][1] - coords[i+1][0]*coords[i][1])

        return abs(sum/2)

#get the coordinates of each fruit
def getFruitCoords(app, fruit, x, y, dx, dy):

    x += dx
    y += dy

    if fruit == 'apple':
        return [x, y, x+20, y+40, x+50, y+40, 
                x+70, y, x+50, y-25, x+20, y-25]
    elif fruit == 'orange' or fruit == 'bomb':
        return [x, y, x+10, y+30, x+50, y+30, 
            x+60, y, x+50, y-30, x+10, y-30]
    elif fruit == 'banana':
        return [x, y, x+20, y+40, x+20, y-40]
    else: #watermelon 
        return [x, y, x+15, y+40, x+100, y+40, 
            x+115, y, x+100, y-40, x+15, y-40]

def updateFruitPosition(app):
    for fruit in app.fruits:
        
        #find new position of fruit using kinematic equations
        x, y = fruit.coords[0], fruit.coords[1]
        accel = 200
        dx = fruit.vx*(1/10)
        dy = fruit.vy*(1/10) + 0.5*accel*(1/100)
        fruit.vy += accel*(1/10)

        #update split fruits by adding a constant to every coordinate 
        if fruit.name == 'split':
            x += dx
            y += dy

            coordsX = list(np.asarray(fruit.addListX) + x)
            coordsY = list(np.asarray(fruit.addListY) + y)

            coords = combineListAlternating(coordsX, coordsY)
            fruit.coords = coords
        else:
            fruit.coords = getFruitCoords(app, fruit.name, x, y, dx, dy)

        fruit.x, fruit.y = fruit.coords[0], fruit.coords[1]
        
        #Remove fruits not on screen to increase efficiency 
        if y < app.height-10:
            fruit.beenOnScreen = True
        if (y > app.height + 10) and fruit.beenOnScreen:
            app.fruits.remove(fruit)

#slice the fruit
def sliceFruit(app):
    for f in app.fruits:
        if (app.sliceLine is not None): #if line is there and fruit isnt sliced
            polygons = f.split(app.sliceLine) #if polygon can be sliced
            if polygons:
                if f.name != 'bomb': #if not a bomb
                    if time.time() - f.timeSinceLastSlice > 0.7: #if the fruit can be sliced again
                        app.sliceNum +=1
                        vx, vy = getVelBlade(app.sliceLine)
                        f1 = Fruit('split', f.color, polyToCoords(polygons[0]), 0, 0, f.timeSinceLastSlice, f.pv//2)
                        f2 = Fruit('split', f.color, polyToCoords(polygons[1]), 0, 0, f.timeSinceLastSlice, f.pv//2)

                        p1 = f1.getArea()/f.getArea()
                        p2 = f2.getArea()/f.getArea()

                        f1.vx, f1.vy = f.vx + vx*p1, f.vy + vy*p1
                        f2.vx, f2.vy = f.vx + vx*p2, f.vy + vy*p2

                        f1.addListX, f1.addListY = createAddList(f1.x,f1.y,f1.coords)
                        f2.addListX, f2.addListY = createAddList(f2.x,f2.y,f2.coords)

                        score = calcScore(f,f1,f2) * (app.sliceNum+1)
                        app.score += score
                        if score > 0:
                            app.scoreList.append(score)
                        
                        app.fruits.remove(f)
                        app.fruits.append(f1)
                        app.fruits.append(f2)

                        f.timeSinceLastSlice = time.time()
                        app.scoreListTime = time.time()

                    if app.sliceNum > 1:
                        app.comboDispTime = time.time()
                else: #if it is a bomb
                    app.bombTime = time.time()
                    app.bombCoords = (f.x, f.y)
                    app.fruits.remove(f)
                    if app.mode == 'gameMode2':
                        app.score -= 25
                    else:
                        app.lives -= 1
                    

#create a list of additional points that are relative to left most point from coords
#used for sliced fruits
def createAddList(x, y, coords):
    x, y = coords[0], coords[1]
    addLX, addLY = [0], [0]

    for i in range(2, len(coords)):
        if i%2==0:
            addLX.append(coords[i] - x)
        else:
            addLY.append(coords[i] - y)
    return addLX, addLY

#pick a random fruit and throw it
def newFruitThrown(app):
    fruitNames = ['apple', 'orange', 'banana', 'watermelon', 'bomb']
    fruitColors = ['red2', 'DarkOrange1', 'yellow', 'green3', 'gray25']
    fruitPVs = [10, 10, 15, 5, 0]

    x,y = random.randint(150, app.width-250), app.height + 220
    
    appleCoords = getFruitCoords(app, 'apple', x, y, 0, 0)
    orangeCoords = getFruitCoords(app, 'orange', x, y, 0, 0)
    bananaCoords = getFruitCoords(app, 'banana', x, y, 0, 0)
    watermelonCoords = getFruitCoords(app, 'watermelon', x, y, 0, 0)
    bombCoords = getFruitCoords(app, 'bomb', x, y, 0, 0)

    fruitCoords = [appleCoords, orangeCoords, bananaCoords, watermelonCoords, bombCoords]

    i = random.randint(0,len(fruitNames)-1)
    app.fruits.append(Fruit(fruitNames[i], fruitColors[i],
                            fruitCoords[i], 0, -500, time.time(), fruitPVs[i])) #starting y velocity

#***************************** SCORING CODE *****************************

#calculate the score based of the sliced fruits
#smaller sliced fruits is weighted more
#more points are awarded for more even slices
def calcScore(f, f1, f2):
    a, a1, a2 = f.getArea(), f1.getArea(), f2.getArea()
    p1, p2 = a1/a*f.pv, a2/a*f.pv
    if min(p1,p2) < 0.1:
        return 0
    return int(min(p1,p2) * 5 + (max(p1,p2)//2))

#adjust the score list so that the recent value is removed
def updateScoreList(app):
    if time.time() - app.scoreListTime > app.scoresTimeReset:
        if len(app.scoreList) > 0:
            app.scoreList.pop(0)
        app.scoreListTime = time.time()

#***************************** POLYGON CODE *****************************

#get the x and y magnitude of a line (y is adjusted)
def getVelBlade(line):
    dx = line[1][0]-line[0][0]
    dy = line[1][1]-line[0][1]
    return dx, dy//3
    
#cited from https://stackoverflow.com/questions/3678869/pythonic-way-to-combine-two-lists-in-an-alternating-fashion
#combines two lists in an alternating fashion
def combineListAlternating(L1,L2):
    result = [None]*(len(L1)+len(L2))
    result[::2] = L1
    result[1::2] = L2
    return result

#polygon - [(x,y),(x,y),(x,y)]
#coords  - [x,y,x,y,x,y]
#converts coordinates to polygon
def coordsToPoly(coords):
    output = []
    for i in range(0,len(coords),2):
        output.append((coords[i], coords[i+1]))
    return output

#polygon - [(x,y),(x,y),(x,y)]
#coords  - [x,y,x,y,x,y]
#converts polygon to coordinates
def polyToCoords(poly):
    output = []
    for p in poly:
        output.append(p[0])
        output.append(p[1])
    return output

#cited from https://rosettacode.org/wiki/Find_the_intersection_of_two_lines#Python
#finds the intersection of two line segments
def findLineIntersections(L1, L2):
    Ax1, Ay1, Ax2, Ay2 = L1[0][0], L1[0][1], L1[1][0], L1[1][1]
    Bx1, By1, Bx2, By2 = L2[0][0], L2[0][1], L2[1][0], L2[1][1]
    d = (By2 - By1) * (Ax2 - Ax1) - (Bx2 - Bx1) * (Ay2 - Ay1)
    if d:
        uA = ((Bx2 - Bx1) * (Ay1 - By1) - (By2 - By1) * (Ax1 - Bx1)) / d
        uB = ((Ax2 - Ax1) * (Ay1 - By1) - (Ay2 - Ay1) * (Ax1 - Bx1)) / d
    else:
        return
    if not(0 <= uA <= 1 and 0 <= uB <= 1):
        return
    x = round(Ax1 + uA * (Ax2 - Ax1), 4)
    y = round(Ay1 + uA * (Ay2 - Ay1), 4)
 
    """ returns a (x, y) tuple or None if there is no intersection """
    return x, y

#takes in a list of coordinates and two points that make up a line
#returns modfied polygon (polygon and interesected indices)
def findPolyLineIntersections(poly, line):
    poly.append(poly[0])
    poly2 = [poly[0]]
    indices = []
    for i in range(len(poly)-1):
        l1 = poly[i:i+2]
        val = findLineIntersections(l1, line)
        if val:
            poly2.append(val)
            indices.append(poly2.index(val))
        poly2.append(poly[i+1])
    return (poly2[:-1], indices)

#takes in modfied polygon (polygon and interesected indices)
#returns a list of coordinates of two polygons 
def slicePolygon(modPoly):
    poly, ind = modPoly
    if len(ind) > 1:
        poly1 = poly[0:ind[0]+1] + poly[ind[1]:]
        poly2 = poly[ind[0]:ind[1] + 1]
        poly1 = list(dict.fromkeys(poly1))
        poly2 = list(dict.fromkeys(poly2))
        return [poly1,poly2]
    else:
        return None

#***************************** KNIFE CODE *****************************

#update knife slicing motion
def updateSlice(app):
    if app.cursor is not None: #keep adding cursor values to cursor trail
        app.sliceList.append(app.cursor)

    delay = 16666666
    if time.time_ns()-app.sliceTime > delay: #if certain time has passed remove oldest point on cursor trail
        if len(app.sliceList) > app.bladePoints + 1:
            app.sliceList.pop(0)
        app.sliceTime = time.time_ns()

    l = app.sliceList #set the cursor trail line to points from cursor trail
    if (l is not None) and (len(l) > app.bladePoints) and (app.cursor is not None):
        x1,y1,x2,y2 = l[0][0], l[0][1], l[2][0], l[2][1]
        app.sliceLine = [(x1, y1), (x2, y2)]
    else:
        app.sliceLine = None


#***************************** CV CODE *****************************

#docs used: https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.html
def setCursor(app, scaled):
    frame = app.frame
    frame = cv2.resize(frame, (540,360)) #lower quality to better frame rate
    frame = cv2.flip(frame, 1) #mirror across y axis to mimic user movement

    grayFrame = cv2.cvtColor(frame ,cv2.COLOR_BGR2GRAY) #convert to grayscale
    smoothFrame = cv2.GaussianBlur(grayFrame, (33,33), 0) #smooth the frame
    ret,thresh = cv2.threshold(smoothFrame, app.minCamThreshold, 255,0) #add threshold
    contours, hierarchy =  cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE) #detect all contours

    #get the biggest circle from all detected contours
    if len(contours) > 0:
        bestC, bestArea = getBiggestContour(contours)
        
        #scale the cursor value based on calibrated playable area
        if scaled:
            oRangeX, nRangeX = (app.xMin,app.xMax), (0,1080) 
            oRangeY, nRangeY = (app.yMin,app.yMax), (0,720) 
            app.scaledx = ((bestC[0] - oRangeX[0])/(oRangeX[1] - oRangeX[0])) * (nRangeX[1] - nRangeX[0])
            app.scaledy = ((bestC[1] - oRangeY[0])/(oRangeY[1] - oRangeY[0])) * (nRangeY[1] - nRangeY[0])
            scaledC = app.scaledx, app.scaledy
        
        #if the contour is big enough (the flashlight and not some spec on the wall)
        if bestArea > app.minContourArea:
            if scaled:
                app.cursor = scaledC
            else:
                app.cursor = bestC
        else:
            app.cursor = None
    else:
        app.cursor = None

def getBiggestContour(contours):
    bestC = (0, 0)
    bestArea = 0
    for c in contours:
            area = cv2.contourArea(c)
            (x,y), r = cv2.minEnclosingCircle(c)
            center = (int(x)*2, int(y)*2) #multiply by 2 to convert from 480p to 720p
            if area > bestArea:
                bestC = center
                bestArea = area
    return bestC, bestArea

#from cmu_112_graphics_openCV
def drawCamera(app, canvas, x, y, frame):
    if frame is None: return
    tkImage = opencvToTk(app, frame)
    canvas.create_image(x,y, image=tkImage)

#from cmu_112_graphics_openCV
def opencvToTk(app, frame):
    """Convert an opencv image to a tkinter image, to display in canvas."""
    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_image)
    tkImage = ImageTk.PhotoImage(image=pil_img)
    return tkImage

def resetBounds(app):
    app.xMin, app.xMax = 535, 545
    app.yMin, app.yMax = 355, 365

def setBestArea(app):
    if app.cursor is not None:
        if app.cursor[0] > app.xMax:
            app.xMax = app.cursor[0]
        elif app.cursor[0] < app.xMin:
            app.xMin = app.cursor[0]
        
        if app.cursor[1] > app.yMax:
            app.yMax = app.cursor[1]
        elif app.cursor[1] < app.yMin:
            app.yMin = app.cursor[1]

#***************************** AUX FUNCTIONS *****************************

def handleCombos(app):
    if app.sliceNum > 1:
        app.comboNum = app.sliceNum
        
    if time.time() - app.comboTime > 0.5:
        #reset the number of fruit sliced every half a second
        app.sliceNum = 0
        app.comboTime = time.time()

def updateFruitDelay(app):
    if app.score < 600:
        #cubic funtion used to determine speed of fruit thrown
        app.fruitDelay = -0.000000041*((app.score-300)**3)+1.375
    else:
        app.fruitDelay = 0.25

def throwNewFruit(app):
    timeBetweenFruit = app.fruitDelay
    if abs(time.time() - app.startTime) > timeBetweenFruit: #if enough time passed throw new fruit
        newFruitThrown(app)
        app.startTime = time.time() #reset fruit throwing time

def handleGameOver(app):
    if app.lives == 0:
        app.gameOver = True
        if app.score > app.highScore: #if new high score
            app.highScore = app.score
            app.overMessage = [f'Score: {app.score}', 'NEW HIGH SCORE!']
        else: #if not a new high score
            app.overMessage = [f'Score: {app.score}', f'High Score: {app.highScore}']
        app.lives = -1 #set lives to -1 so code runs only once

def handleGameOver2(app):
    #TODO CHANGE
    if time.time() - app.gm2Time > app.gm2Countdown:
        app.gameOver = True
        if app.score > app.highScore2: #if new high score
            app.highScore2 = app.score
            app.overMessage = [f'Score: {app.score}', 'NEW HIGH SCORE!']
        else: #if not a new high score
            app.overMessage = [f'Score: {app.score}', f'High Score: {app.highScore2}']
        app.gm2Time = time.time()

#***************************** DRAWING CODE *****************************

def drawExplosion(app, canvas):
    if time.time() - app.bombTime < 0.25:
        x,y = app.bombCoords
        coords = [x, y, x+40, y-20, x+60, y-60, x+80, y-20, x+120, y,
                    x+80, y+20, x+60, y+60, x+40, y+20]
        canvas.create_polygon(coords, fill='orange', outline='red', width=3)
        font = app.font + ' 24 bold'
        canvas.create_text(x+60,y, text='BOOM',fill='red', font=font)

def drawCursor(app, canvas):
    c = app.cursor
    if c is not None:
        canvas.create_oval(c[0]-10,c[1]-10,c[0]+10,c[1]+10, fill='black')
        canvas.create_oval(c[0]-100,c[1]-100,c[0]+100,c[1]+100, outline='green', width=5)

def drawScore(app, canvas):
    canvas.create_text(app.width//2, app.height * 0.1, text = f'SCORE: {app.score}'
                    ,font= app.font + ' 40 bold')
    if app.mode == 'gameMode2':
        timeElapsed =  int(time.time() - app.gm2Time)
        canvas.create_text(app.width//2, 130, text = f'Time: {app.gm2Countdown - timeElapsed}'
                    ,font= app.font + ' 40 bold')

def drawCombo(app, canvas):
    if time.time() - app.comboDispTime < app.scoresTimeReset:
        if app.comboNum > 1:
            canvas.create_text(1000, 680, text = f'COMBO {app.comboNum}X', font= app.font + ' 30 bold', fill='black')

def drawScoreList(app, canvas):
    y = 100
    x = 1000
    scores = app.scoreList[::-1]
    scores = scores[:15]
    for s in scores:
        canvas.create_text(x, y, text = f'+ {s}', font= app.font + ' 30 bold', fill='black')
        y += 35

def drawLives(app, canvas):
    x,y = 25, 670
    for lives in range(app.lives):
        coords = [x,y,x+30,y+30,x+60,y,x+45,y-15,x+30,y,x+15,y-15]
        canvas.create_polygon(coords, fill='deep pink', outline='black', width=3)
        x += 80

def drawGameOver(app, canvas):
    if app.gameOver:
        canvas.create_text(app.width//2, app.height//2-80, text = 'GAME OVER'
                    ,font= app.font + ' 40 bold')
        canvas.create_text(app.width//2, app.height//2-30, text = app.overMessage[0]
                    ,font= app.font + ' 30 bold')
        canvas.create_text(app.width//2, app.height//2+20, text = app.overMessage[1]
                    ,font= app.font + ' 30 bold')

        canvas.create_text(app.width//2, app.height//2+140, text = 'Press R To Restart'
                    ,font= app.font + ' 30 bold')
        canvas.create_text(app.width//2, app.height//2+180, text = 'Press H To Access The Menu'
                    ,font= app.font + ' 30 bold')

def drawFruits(app, canvas):
    for fruit in app.fruits:
        if fruit.name == 'bomb':
            canvas.create_polygon(fruit.coords, fill=fruit.color, outline='red', width=6)
        else:
            canvas.create_polygon(fruit.coords, fill=fruit.color, outline='black', width=1)

def drawSlice(app, canvas):
    l = app.sliceList
    if (l is not None) and (len(l) > app.bladePoints) and (app.cursor is not None):
        canvas.create_line(l[0][0], l[0][1], l[app.bladePoints-1][0], l[app.bladePoints-1][1], width=3)

#modes code from: https://www.cs.cmu.edu/~112/notes/notes-animations-part4.html#usingModes
#***************************** SPLASH SCREEN *****************************

def splashScreenMode_sizeChanged(app):
    app.setSize(1080, 720)

def splashScreenMode_redrawAll(app, canvas):
    canvas.create_rectangle(0, 0, app.width, app.height, fill='AntiqueWhite1')
    font = app.font + ' 50 bold'
    canvas.create_text(app.width/2, 300, text='Welcome to Berry Samurai!', font=font)
    canvas.create_text(app.width/2, 400, text='Press any key to continue to camera calibration', font=font)

def splashScreenMode_keyPressed(app, event):
    app.mode = 'calibration'

#***************************** CALIBRATION SCREEN *****************************

def calibration_sizeChanged(app):
    app.setSize(1080, 720)

def calibration_redrawAll(app, canvas):
    canvas.create_rectangle(0, 0, app.width, app.height, fill='AntiqueWhite1') #bg

    font= app.font + ' 20 bold'
    drawCamera(app, canvas, app.width - 800, app.height - 200, app.calFrame)

    canvas.create_text(app.width/2, 50, text='First hold your phone with the flashlight on at the desired distance you would like to play from', font=font)
    canvas.create_text(app.width/2, 80, text='Make the threshold value as small as you can without any other white blobs appearing besides your flashlight', font=font)
    canvas.create_text(app.width/2, 110, text='Suggested Threshold Values: 230 - 250', font=font)
    
    canvas.create_text(app.width/2, 160, text='Move your flashlight around the intended play zone', font=font)
    canvas.create_text(app.width/2, 190, text='Adjust the min value area until it is green when you move it around the entire play zone', font=font)
    canvas.create_text(app.width/2, 220, text='Suggested Area Values: 500-3000', font=font)

    canvas.create_text(app.width/2, 270, text='Use the left and right keys to adjust the threshold value', font=font)
    canvas.create_text(app.width/2, 300, text='Use the up and down keys to adjust the min area of light', font=font)

    font= app.font + ' 30 bold'
    canvas.create_text(app.width - 250, 430, text= f'current threshold value: {app.minCamThreshold}', font=font)
    if app.calibrationArea - app.minContourArea > 100:
        canvas.create_text(app.width - 250, 480, text= f'current min Area: {app.minContourArea}', font=font, fill='green')
    else:
        canvas.create_text(app.width - 250, 480, text= f'current min Area: {app.minContourArea}', font=font)
    canvas.create_text(app.width - 250, 530, text= f'desired min Area: {app.calibrationArea}', font=font)

    canvas.create_text(app.width - 250, 600, text='Press Enter to continue', font=font)

def calibration_keyPressed(app, event):
    if event.key == 'Enter':
        app.mode = 'calibration2'

    if event.key == 'Up': #increase threshold value
        if app.minCamThreshold < 255:
            app.minCamThreshold += 1
    elif event.key == 'Down': #decrease threshold value
        if app.minCamThreshold > 150:
            app.minCamThreshold -= 1
    elif event.key == 'Left': #decrease min value
        if app.minCamThreshold > 0:
            app.minContourArea -= 100
    elif event.key == 'Right': #increase min value
        if app.minCamThreshold < 20000:
            app.minContourArea += 100

def calibration_cameraFired(app):
    app.calFrame = cv2.resize(app.frame, (540,360)) #reduce cam size to inc frame rate
    app.calFrame = cv2.flip(app.calFrame, 1) #flip over y axis to mirror user 

    grayFrame = cv2.cvtColor(app.calFrame ,cv2.COLOR_BGR2GRAY) #convert to grayscale
    smoothFrame = cv2.GaussianBlur(grayFrame, (33,33), 0) #smooth the frame with blur
    ret,thresh = cv2.threshold(smoothFrame, app.minCamThreshold, 255,0) #add threshold to find contours
    app.calFrame = thresh #set calibration frame to new frame

    contours, hierarchy =  cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE) #detect all contours
    c, app.calibrationArea = getBiggestContour(contours)

#***************************** CALIBRATION 2 SCREEN *****************************

def calibration2_sizeChanged(app):
    app.setSize(1080, 720)

def calibration2_redrawAll(app, canvas):
    canvas.create_rectangle(0,0,app.width,app.height,fill='AntiqueWhite1') #draw background

    drawCamera(app, canvas, app.width/2, app.height - 200, app.calFrame) #draw camera

    #draw text u need
    font= app.font + ' 30 bold'
    canvas.create_text(app.width/2, 100, text='You Will Use Your Phone Flashlight To Play This Game', font=font)
    canvas.create_text(app.width/2, 140, text='Move Your Phone With The Flashlight On To Adjust Your Comfortable Playing Area', font=font)
    canvas.create_text(app.width/2, 180, text='Press R To Reset The Playing Area', font=font)
    canvas.create_text(app.width/2, 220, text='Press Enter To Continue When You Are Finished', font=font)

    #draw xmin xmax ymin ymax on camera screem w scaled values
    sxMin = app.xMin / 720 * 360
    sxMax = app.xMax / 720 * 360
    syMin = app.yMin / 1080 * 540
    syMax = app.yMax / 1080 * 540
    
    canvas.create_line(sxMin+270, 340, sxMin+270, 700, fill='blue', width=3)
    canvas.create_line(sxMax+270, 340, sxMax+270, 700, fill='blue', width=3)
    canvas.create_line(270, syMin+350, 810, syMin+350, fill='blue', width=3) 
    canvas.create_line(270, syMax+350, 810, syMax+350, fill='blue', width=3)

def calibration2_keyPressed(app, event):
    if event.key == 'Enter':
        app.mode = 'rules'

    if event.key == 'r':
        resetBounds(app)

def calibration2_timerFired(app):
    setBestArea(app) #adjusts the playable area of the game based on users movement

def calibration2_cameraFired(app):
    app.calFrame = cv2.resize(app.frame, (540,360))# resize the frame for better frame rate 
    app.calFrame = cv2.flip(app.calFrame, 1) # mirror over the y axis

    grayFrame = cv2.cvtColor(app.calFrame, cv2.COLOR_BGR2GRAY) #convert to grayscale
    app.calFrame = grayFrame #set the calibration frame to the new frame

    setCursor(app, False) #set the center of the cursor on screen

#***************************** RULES SCREEN *****************************

def rules_sizeChanged(app):
    app.setSize(1080, 720)

def rules_redrawAll(app, canvas):
    canvas.create_rectangle(0, 0, app.width, app.height, fill='AntiqueWhite1')

    font= app.font + ' 60 bold'
    canvas.create_text(app.width/2, 50, text= 'RULES', font=font)

    canvas.create_line(0, 93, app.width, 93, width=3)

    font= app.font + ' 30 bold'
    canvas.create_text(app.width/2, 125, text= 'Game Mode 1', font=font)
    canvas.create_text(app.width/2, 165, text= 'Slice Fruits to Gain Points', font=font)
    canvas.create_text(app.width/2, 205, text= 'Avoid the Black Bombs Or You Will Lose Lives', font=font)
    canvas.create_text(app.width/2, 245, text= 'When You Lose All 3 Lives, The Game Is Over', font=font)

    canvas.create_line(0, 280, app.width, 280, width=3)

    canvas.create_text(app.width/2, 310, text= 'Game Mode 2', font=font)
    canvas.create_text(app.width/2, 350, text= 'Slice Fruits to Gain Points', font=font)
    canvas.create_text(app.width/2, 390, text= 'Avoid the Black Bombs Or You Will Lose Points', font=font)
    canvas.create_text(app.width/2, 430, text= 'You Have 90 Seconds To Get As Many Points As Possible', font=font)

    canvas.create_line(0, 465, app.width, 465, width=3)

    canvas.create_text(app.width/2, 505, text= 'Press H To Access The Main Menu', font=font)
    canvas.create_text(app.width/2, 545, text= 'Press C To Recalibrate Your Camera', font=font)
    canvas.create_text(app.width/2, 585, text= 'Press Q To Quit The Game', font=font)

    canvas.create_line(0, 625, app.width, 625, width=3)

    canvas.create_text(app.width/2, 665, text= 'Press 1 or 2 for Game Modes 1 and 2 respectively', font=font)

def rules_keyPressed(app, event):

    if event.key == 'c':
        app.mode = 'calibration'
    elif event.key == 'q':
        App._theRoot.app.quit()
   
    if event.key == '1':
        appRestart(app)
        app.mode = 'gameMode1'
    elif event.key == '2':
        appRestart(app)
        app.mode = 'gameMode2'

#***************************** MAIN GAME MODE *****************************

def gameMode1_sizeChanged(app):
    app.setSize(1080, 720)

def gameMode1_redrawAll(app, canvas):
    canvas.create_rectangle(0, 0, app.width, app.height, fill='AntiqueWhite1') #bg

    drawFruits(app, canvas) #draw all the fruits

    drawSlice(app, canvas) #draw the trailing cursor that follows the main cursor
    drawCursor(app, canvas) #draw the dot and circle cursor 

    if not app.gameOver:
        drawLives(app, canvas) #draw the # of lives if game isnt over
        drawScore(app, canvas) #draw the score at top if game isnt over
        drawScoreList(app, canvas) #draw the list of added scores
    
    drawCombo(app, canvas) #draw multiplier if a combo is hit

    drawExplosion(app, canvas) #draws the explosion of the bomb when sliced

    drawGameOver(app, canvas) #draw the game over screen with score and high score

def gameMode1_keyPressed(app, event):
    if event.key == "q":
        App._theRoot.app.quit()
    
    if event.key == 'r':
        appRestart(app)

    if event.key == 'h':
        app.mode = 'rules'

    #DEBUGGING PURPOSES
    if event.key == 'Up':
        app.score += 150
    if event.key == 'Down':
        app.lives -= 1

def gameMode1_timerFired(app):
    updateFruitDelay(app) #update the speed at which fruits are thrown based off score
    handleCombos(app) #handle combos for when multiple fruits are sliced

    updateSlice(app) #update the slicing motion (blade/knife)
    updateFruitPosition(app) #update fruit position of every fruit
    if not app.gameOver:
        sliceFruit(app) #check if sliced and slice fruit if needed
        throwNewFruit(app) #throw a new fruit after a period of time
    updateScoreList(app) #update the list of added scores

    handleGameOver(app) #handle game over message and lives 

def gameMode1_cameraFired(app):
    setCursor(app, True) #set the center of the cursor on screen

#***************************** 2nd GAME MODE *****************************

def gameMode2_sizeChanged(app):
    app.setSize(1080, 720)

def gameMode2_redrawAll(app, canvas):
    canvas.create_rectangle(0, 0, app.width, app.height, fill='AntiqueWhite1') #bg

    drawFruits(app, canvas) #draw all the fruits

    drawSlice(app, canvas) #draw the trailing cursor that follows the main cursor
    drawCursor(app, canvas) #draw the dot and circle cursor 

    if not app.gameOver:
        drawScore(app, canvas) #draw the score at top if game isnt over
        drawScoreList(app, canvas) #draw the list of added scores
    drawCombo(app, canvas) #draw multiplier if a combo is hit

    drawExplosion(app, canvas) #draws the explosion of the bomb when sliced

    drawGameOver(app, canvas) #draw the game over screen with score and high score

def gameMode2_keyPressed(app, event):
    if event.key == "q":
        App._theRoot.app.quit()
    
    if event.key == 'r':
        appRestart(app)

    if event.key == 'h':
        app.mode = 'rules'

    #DEBUGGING PURPOSES
    if event.key == 'Up':
        app.score += 150
    if event.key == 'Down':
        app.gm2Time -= 10
    
def gameMode2_timerFired(app):
    updateFruitDelay(app) #update the speed at which fruits are thrown based off score
    handleCombos(app) #handle combos for when multiple fruits are sliced

    updateSlice(app) #update the slicing motion (blade/knife)
    updateFruitPosition(app) #update fruit position of every fruit
    if not app.gameOver:
        sliceFruit(app) #check if sliced and slice fruit if needed
        throwNewFruit(app) #throw a new fruit after a period of time
    updateScoreList(app) #update the list of added scores

    handleGameOver2(app) #handle game over message and lives

def gameMode2_cameraFired(app):
    setCursor(app, True) #set the center of the cursor on screen

#***************************** MAIN APP *****************************
runApp(width=1080, height=720)