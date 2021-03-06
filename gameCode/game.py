import sys, pygame, config, random, time
import player, enemy, board, bomb, highscore, music, agent, observableState
from pygame.locals import *
import os,sys
sys.path.append(os.path.split(sys.path[0])[0])
from Net import *

class Game:
	players = []
	enemies = []
	bombs = []
	resetTiles = []
	stage = 1
	level = 1
	firstRun = True
	exitGame = False

	# multiplayer data
	tcpData = [] 
	sendingData = []
	lastTcpCall = 0
	pHash = {}

	# agent related data
	userPrevScore = 0
	userEvent = "continue"
	epochs = 0
	playerAlgo = "random"

	def __init__(self, mode, playerAlgo, epochs, isLoad, isSave, isGraphics, eps, isTest):
		self.epochs = epochs
		self.playerAlgo = playerAlgo
		self.isLoad = isLoad
		self.isSave = isSave
		self.eps = eps
		annealRate = self.eps/self.epochs
		print annealRate
		self.agent = agent.Agent(playerAlgo, isLoad, eps, annealRate, isTest)
		self.isGraphics = isGraphics

		self.c = config.Config()

		# self.highscores = highscore.Highscore()
		self.forceQuit = False
		self.mode = mode
		self.initVar()

		if self.isGraphics:
			pygame.init()
			self.screen = pygame.display.set_mode((self.c.WIDTH,self.c.HEIGHT),pygame.DOUBLEBUF)
			pygame.display.set_caption("Bomberman")
			
		# init preloader / join server
		if self.mode == self.c.MULTI:
			preloader = pygame.image.load(self.c.IMAGE_PATH + "loading.png").convert()
			self.blit(preloader,(0,0))
			pygame.display.flip()
			self.joinGame()

		for i in range(self.epochs):
			# repeat for multiple levels
			print "Running Epoch " + str(i)
			self.stage = 6
			# self.level = random.randint(1,4)
			self.level = 4
			self.resetGame()
			if self.isGraphics:
				self.clearBackground()
			self.initGame()
			print "Player Score - " + str(self.user.score)
			self.initVar()

			# Save after every 10000 epochs
			if((i+1)%10000 == 0):
				if isSave:
					self.agent.saveModel()
		if isSave:
			self.agent.saveModel()

		# # launch highscores
		# if not self.forceQuit:
		# 	self.highscores.reloadScoreData()
		# 	self.highscores.displayScore()

	def initVar(self):
		self.players = []
		self.enemies = []
		self.bombs = []
		self.resetTiles = []
		self.stage = 1
		self.level = 1
		self.firstRun = True
		self.exitGame = False
		self.userPrevScore = 0

	def joinGame(self):
		self.client = TCPClient()

		# choose server connection
		if self.c.LOCALHOST:
			self.client.connect("localhost",6317)
		else:
			self.client.connect("67.23.28.146",6317)

		self.id = random.randint(0,1000000)		# unique player id
		self.client.send_data(["update","user joined",str(self.id)])

		while True:
			self.tcpData = self.client.wait_for_data()
			self.client.send_data(["update",None])
			print self.tcpData
			self.initMultiUsers()
			if self.tcpData[-1] == "[SERVER]|START":
				break
	
	def getMultiStartPosition(self,id):
		if id == "1":
			return (40,40)
		elif id == "2":
			return (760,40)
		elif id == "3":
			return (40,600)
		elif id == "4":
			return (760,600)

	def initMultiSelf(self,data):
		d = data[-1].split("|")
		self.user = player.Player("Player " + ary[0] ,"p_"+ary[0]+"_" , ary[2], self.getMultiStartPosition(ary[0]))
		self.players.append(self.user)

	def initMultiUsers(self):
		for element in self.tcpData:
			ary = element.split("|")
			if ary[0] > self.lastTcpCall:
				# manipulate
				if ary[1] == 'JOIN':
					p = player.Player("Player "+ary[0] ,"p_"+ary[0]+"_" , ary[2], self.getMultiStartPosition(ary[0]))
					self.pHash[ary[2]] = p
					self.players.append(p)
					self.lastTcpCall = ary[0]

	def tcpUpdate(self):
		data = self.client.check_for_data()
		if data:
			self.tcpData = data
	#		print '-------------'
	#		print self.tcpData
			if self.sendingData == []:
				self.sendingData = ["update",None]
			self.client.send_data(self.sendingData)
			self.sendingData = []
	
	# RFCT
	# ary[3] = key 			ary[2] = user
	def manipulateTcpData(self):
		for d in self.tcpData:
			ary = d.split("|")
			try:
				print ary[0] + " " + str(self.lastTcpCall)
				if int(ary[0]) > int(self.lastTcpCall):
 					if str(ary[2]) != str(self.id):
						if ary[1] == "MOVE":
							point = self.pHash[ary[2]].movement(int(ary[3]))
							self.movementHelper(self.pHash[ary[2]],point)
						elif ary[1] == "BOMB":
							self.deployBomb(self.pHash[ary[2]])
					self.lastTcpCall = ary[0]
			except ValueError:
				print 'skip'

	def resetGame(self):
		self.field = None
		self.enemies = []
		self.bombs = []
		self.resetTiles = []

	def clearBackground(self):
		bg = pygame.Surface(self.screen.get_size())
		bg = bg.convert()
		bg.fill((0,0,0))
		self.blit(bg,(0,0))

	def initGame(self):
		if self.mode == self.c.SINGLE:
			if self.isGraphics:
				self.printText("Level %d-%d" % (self.stage,self.level),(40,15))
			self.field = board.Board(self.stage, self.level, self.isGraphics)
			self.timer = 3*60+1
		elif self.mode == self.c.MULTI:
			self.printText("Multiplayer",(40,15))
			self.field = board.Board(0,0)
			self.timer = 5*60+1

		if self.isGraphics:
			self.drawBoard()
			self.drawInterface()

		# players do not have to be reinitialized in single player after the first time
		if self.firstRun:
			self.firstRun = False
			self.initPlayers()
		else:
			self.resetPlayerPosition(self.user,False)
		
		self.updateTimer()
		
		# no enemies in multiplayer
		if self.mode == self.c.SINGLE:
			self.initEnemies()
		
		# music player
		# mp = music.Music()
		# mp.playMusic(self.mode)

		self.runGame()

	# draws the board onto the screen
	def drawBoard(self):
		for row in range(1,len(self.field.board)-1):
			for col in range(1,len(self.field.board[row])-1):
				image = self.field.board[row][col].image
				# RFCT - fix the mess \/
				position = self.field.board[row][col].image.get_rect().move((col*self.c.TILE_SIZE,row*self.c.TILE_SIZE))
				self.blit(image, position)

	def updateDisplayInfo(self):
		self.printText(self.user.score,(65,653))
		self.printText(self.user.lives,(775,653))
		self.printText(self.user.maxBombs,(630,653))
		self.printText(self.user.power,(700,653))

	def drawInterface(self):
		player  = pygame.image.load(self.c.IMAGE_PATH + "screen/player.png").convert()
		life = pygame.image.load(self.c.IMAGE_PATH + "screen/life.png").convert()
		bomb = pygame.image.load(self.c.IMAGE_PATH + "screen/bomb.png").convert()
		power = pygame.image.load(self.c.IMAGE_PATH + "screen/power.png").convert()
		clock = pygame.image.load(self.c.IMAGE_PATH + "screen/clock.png").convert()

		self.blit(player,(40,650))
		self.blit(clock,(365,650))

		self.blit(bomb,(590,647))
		self.blit(power,(670,650))
		self.blit(life,(740,652))
	
	def initPlayers(self):
		if self.mode == self.c.SINGLE:
			self.user = player.Player("Player 1","p_1_",0,(40,40),self.agent, self.isGraphics)
			self.players.append(self.user)
			if self.isGraphics:
				self.blit(self.user.image, self.user.position)
		elif self.mode == self.c.MULTI:
			for p in self.players:
				if str(p.id) == str(self.id):
					self.user = p
				self.blit(p.image,p.position)

	def initEnemies(self):
		# generates 5 enemies
		for i in range(0,1):
			while True:
				x = random.randint(3,self.field.width-2)*40			# randint(1,X) changed to 6 so enemies do not start near player
				# TODO
				y = random.randint(4,self.field.height-2)*40
				# x = 1*40
				# y = 4*40
				# y = 40
				# print x,y
				if self.field.getTile((x,y)).canPass() == True:
					break

			e = enemy.Enemy("Enemy", "e_%d_" % (random.randint(1,self.c.MAX_ENEMY_SPRITES)), (x,y), self.isGraphics)
			self.enemies.append(e)
			if self.isGraphics:
				self.blit(e.image, e.position)

	def runGame(self):
		# Set the start state
		self.user.agent.setState(self.getObservableState())

		if self.isGraphics:
			clock = pygame.time.Clock()
			pygame.time.set_timer(pygame.USEREVENT,120)
			pygame.time.set_timer(pygame.USEREVENT+1,60)
		
		cyclicCounter = 0
		self.gameIsActive = True

		while self.gameIsActive:
			if self.isGraphics:
				clock.tick(self.c.FPS)
			
			self.checkPlayerEnemyCollision()
			self.checkWinConditions()
			# self.field.printBoard()

			# MULTIPLAYER
			if self.mode == self.c.MULTI:
				self.tcpUpdate()
				self.manipulateTcpData()

			# self.c.FPS is set to 30, 30 ticks = 1 second
			cyclicCounter += 1
			if cyclicCounter == 3:
				cyclicCounter = 0
				self.updateTimer()

			if cyclicCounter%3 == 1:
				self.clearExplosion()

			self.updateBombs()

			# Get action from agent
			move = self.user.agent.get_action()
			# print move
			if move == "up":
				if self.isGraphics:
					self.user.getImage('up')
				self.movementHelper(self.user, [0, -1*self.c.TILE_SIZE])
				# sys.stdout.write("UP\n")
			elif move == "down":
				if self.isGraphics:
					self.user.getImage('down')
				self.movementHelper(self.user, [0, 1*self.c.TILE_SIZE])
				# self.user.setScore(80)
				# sys.stdout.write("DOWN\n")
			elif move == "left":
				if self.isGraphics:
					self.user.getImage('left')
				self.movementHelper(self.user, [-1*self.c.TILE_SIZE, 0])
				# sys.stdout.write("LEFT\n")
			elif move == "right":
				if self.isGraphics:
					self.user.getImage('right')
				self.movementHelper(self.user, [1*self.c.TILE_SIZE, 0])
				# sys.stdout.write("RIGHT\n")
			elif move == "bomb":
				self.deployBomb(self.user)
				# sys.stdout.write("BOMB\n")
			elif move == "stay":
				# Do nothing
				# sys.stdout.write("STAY\n")
				pass
			else:
				# ERROR
				assert (False), "WRONG ACTION"

			for e in self.enemies:
				probToMove = random.random()
				if(probToMove <= self.c.ENEMY_MOVE_PROB):	
					self.movementHelper(e,e.nextMove())

			if self.isGraphics:
				self.updateDisplayInfo()
				pygame.display.update()

			if self.isGraphics:
				for event in pygame.event.get():
					if event.type == pygame.QUIT:
						self.forceQuit()
				# elif event.type == pygame.KEYDOWN:
				# 	# deploy bomb
				# 	k = event.key

				# 	if k == pygame.K_SPACE:
				# 		if self.mode == self.c.MULTI:
				# 			self.sendingData = ["update","bomb",k,self.id]
				# 		self.deployBomb(self.user)
				# 	elif k == pygame.K_ESCAPE:
				# 		self.fQuit()
				# 	elif k == pygame.K_UP or k == pygame.K_DOWN or k == pygame.K_LEFT or k == pygame.K_RIGHT:
				# 		if self.mode == self.c.MULTI:
				# 			self.sendingData = ["update","movement",k,self.id]

				# 		# player's move method
				# 		point = self.user.movement(k) # next point
				# 		self.movementHelper(self.user, point)
				# 	elif k == pygame.K_g: # god mode, cheat ;)
				# 		self.user.gainPower(self.c.BOMB_UP)
				# 		self.user.gainPower(self.c.POWER_UP)

				# elif event.type == pygame.USEREVENT: # RFCT - change definition
				# 	self.updateBombs()
				# elif event.type == pygame.USEREVENT+1: #RFCT
				

				# self.updateDisplayInfo()
				# pygame.display.update()

			# Return observations and reward to agent
			state = self.getObservableState()
			reward = self.getReward()
			event = self.getEvent()
			self.user.agent.observe(state, reward, event)
			# self.user.agent.extract_features(state)

	def getObservableState(self):
		enemies = []
		bombs = []
		# Enemy Position
		for enemy in self.enemies:
			enemies.append(enemy)

		# Bombs	
		for bomb in self.bombs:
			bombs.append(bomb)

		newState = observableState.ObservableState(self.field, self.user.position, enemies, bombs, self.user)
		return newState

	def getReward(self):
		reward = self.user.score - self.userPrevScore
		self.userPrevScore = self.user.score
		return reward

	def getEvent(self):
		return self.userEvent

	def deployBomb(self,player):
		b = player.deployBomb() # returns a bomb if available
		if b != None:
			tile = self.field.getTile(player.position)
			tile.bomb = b
			self.bombs.append(b)
			expectedReward = self.expectedBombReward(b)
			self.user.setScore(expectedReward)

	def blit(self,obj,pos):
		if self.isGraphics:
			self.screen.blit(obj,pos)
	#	pygame.display.flip()
	
	def movementHelper(self, char, point):
		nPoint = char.position.move(point)

		tile = self.field.getTile(nPoint)

		# also check for bomb / special power ups here
		if tile.canPass():
			if char.instance_of == 'player' and tile.isPowerUp():
				# char.setScore(200) # RFCT | BUG - VARIES DEPENDING ON POWER UP
				char.gainPower(tile.type)
				tile.destroy()
				if self.isGraphics:
					self.blit(tile.getBackground(),nPoint)
			char.move(point)
			
			if self.isGraphics:
				self.blit(char.image, char.position)

			t = self.field.getTile(char.old)
			if self.isGraphics:
				if t.bomb != None:
					self.blit(t.getBackground(),char.old)
				self.blit(t.getImage(), char.old)

	def updateBombs(self):
		for bomb in self.bombs:
			if bomb.tick() == 0:
				self.activateBomb(bomb)
	
	def activateBomb(self,bomb):
		if not bomb.triggered:
			bomb.explode()
			self.triggerBombChain(bomb)
			self.bombs.remove(bomb)
			tile = self.field.getTile(bomb.position)
			tile.bomb = None
			if self.isGraphics:
				self.blit(tile.getImage(), bomb.position)
			self.resetTiles.append(bomb.position)

			if self.isGraphics:
				explosion = pygame.image.load(self.c.IMAGE_PATH + "explosion_c.png").convert()
				self.blit(explosion,bomb.position)

	def triggerBombChain(self, bomb):
		if bomb == None:
			return
		else:
			bomb.triggered = True
			self.checkPlayerEnemyBombCollision(bomb.position)	
			self.bombHelper(bomb,'left')	
			self.bombHelper(bomb,'right')
			self.bombHelper(bomb,'up')
			self.bombHelper(bomb,'down')
	
	# ALGO NEEDS RFCT!!!
	def bombHelper(self, bomb, direction):
		if direction == 'right':
			point = (40,0)
		elif direction == 'left':
			point = (-40,0)
		elif direction == 'up':
			point = (0,-40)
		elif direction == 'down':
			point = (0,40)

		x = y = 0
		while True:
			x += point[0]
			y += point[1]

			nPoint = bomb.position.move((x,y))
			t = self.field.getTile(nPoint)
			
			# hit a block or indestructible object
			if not t.canBombPass():
				# trigger new bomb explosion
				if t.bomb != None:
					self.activateBomb(t.bomb)
				elif t.destroyable == True:
					# if brick or powerup or player
					t.destroy()
					if self.isGraphics:
						self.blit(t.getImage(),nPoint)
					# self.user.setScore(50)
				break
			else:
				# path which explosion can travel on
				self.checkPlayerEnemyBombCollision(nPoint)

				if self.isGraphics:
					explosion = pygame.image.load(self.c.IMAGE_PATH + "explosion_c.png").convert()
					self.blit(explosion,nPoint)
				self.resetTiles.append(nPoint)
			
			# check bomb's power, this terminates the recursive loop
			if int(abs(x)/40) == bomb.range or int(abs(y)/40) == bomb.range:
				#	print "(x,y) => (" + str(x) + "," + str(y) + ")"
				break
	
	def clearExplosion(self):
		for point in self.resetTiles:
			t = self.field.getTile(point)
			if self.isGraphics:
				self.blit(t.getImage(),point)
			self.resetTiles.remove(point)

	def resetPlayerPosition(self, player, death):
		player.reset(death)
		if self.isGraphics:
			self.blit(player.image,player.position)

	def checkPlayerEnemyBombCollision(self, position):
		# check if player was hit by bomb
		for player in self.players:
			if player.position == position:
				self.userEvent = "death"
				self.user.setScore(-2.0)
				if player.loseLifeAndGameOver():
					self.gameover(player)
				else:
					# if the player gets hit by a blast, reset it's position to the starting position
					self.resetPlayerPosition(player,True)
		
		# check if enemy was hit by bomb
		for enemy in self.enemies:
			if enemy.position == position:
				# Add reward here 
				self.enemies.remove(enemy)
				self.user.setScore(2.0)

	def checkPlayerEnemyCollision(self):
		for enemy in self.enemies:
			if enemy.position == self.user.position:
				self.userEvent = "death"
				# RFCT - code repetition
				if self.user.loseLifeAndGameOver():
					self.gameover(self.user)
				self.user.setScore(-2.0)
				self.resetPlayerPosition(self.user,True)
	
	def checkWinConditions(self):
		if self.mode == self.c.SINGLE:
			if len(self.enemies) == 0:
				self.victory()

	def gameover(self, player):
		if self.mode == self.c.SINGLE:
			# print 'gameover - lost all lives | or time ran out'
			# self.highscores.addScore(player.score)
			self.gameIsActive = False
			
			# DONT EXIT GAME
			# self.exitGame = True
	
	def fQuit(self):
		self.gameIsActive = False
		self.exitGame = True
		self.forceQuit = True

	def printText(self,text,point):
		font = pygame.font.Font("lucida.ttf",20)
	#	font = pygame.font.SysFont("resources/fonts/Lucida Console",26)
		label = font.render(str(text)+'  ', True, (255,255, 255), (0, 0, 0))
		textRect = label.get_rect()
		textRect.x = point[0] 
		textRect.y = point[1]
		self.blit(label, textRect)
	
	def victory(self):
		self.gameIsActive = False
		self.user.setScore(0.5)
		self.level += 1
		if self.level > 6:
			self.stage += 1
			self.level = 1
		# mp = music.Music()
		# mp.playSound("victory")
		time.sleep(2)

	def updateTimer(self):
		self.timer -= 1
		# self.user.setScore(-1)

		# user lost
		if self.timer == 0:
			# self.user.setScore(-500)
			self.gameover(self.user)

		mins = str(int(self.timer/60))
		secs = str(int(self.timer%60))

		if len(mins) == 1:
			mins = "0"+mins
		if len(secs) == 1:
			secs = "0"+secs
		txt = "%s:%s" % (mins,secs)
		if self.isGraphics:
			self.printText(txt,(400,653))


	def expectedBombNumBricks(self, bomb):
		x = self.user.position[0]/self.c.TILE_SIZE
		y = self.user.position[1]/self.c.TILE_SIZE
		bomb_range = bomb.range
		brick = self.c.BRICK
		wall = self.c.WALL
		board = self.field.board

		numBricks = 0

		for i in range(bomb_range):
			if (board[y+i+1][x].type == brick):
				numBricks += 1
				break
			elif (board[y+i+1][x].type == wall):
				break

		for i in range(bomb_range):
			if (board[y-i-1][x].type == brick):
				numBricks += 1
				break
			elif (board[y-i-1][x].type == wall):
				break

		for i in range(bomb_range):
			if (board[y][x+i+1].type == brick):
				numBricks += 1
				break
			elif (board[y][x+i+1].type == wall):
				break

		for i in range(bomb_range):
			if (board[y][x-i-1].type == brick):
				numBricks += 1
				break
			elif (board[y][x-i-1].type == wall):
				break

		return numBricks

	def probEnemyDie(self, x, y, bomb_range, bomb_fuse, ex, ey):
		# Termination cases
		# print (ex,ey,bomb_fuse)
		if(bomb_fuse == 1):
			for i in range(bomb_range):
				if((x == ex and y+i+1 == ey) or (x == ex and y-i-1 == ey) or (x+i+1 == ex and y == ey) or (x-i-1 == ex and y == ey)):
					return 1
			return 0

		# Call next round
		prob = 0
		bomb_fuse -= 1
		probStay = self.probEnemyDie(x, y, bomb_range, bomb_fuse, ex, ey)

		probMove = 0
		if(self.field.board[ey][ex+1].canPass()):
			probMove += 0.25*self.probEnemyDie(x, y, bomb_range, bomb_fuse, ex+1, ey)
		if(self.field.board[ey][ex-1].canPass()):
			probMove += 0.25*self.probEnemyDie(x, y, bomb_range, bomb_fuse, ex-1, ey)
		if(self.field.board[ey+1][ex].canPass()):
			probMove += 0.25*self.probEnemyDie(x, y, bomb_range, bomb_fuse, ex, ey+1)
		if(self.field.board[ey-1][ex].canPass()):
			probMove += 0.25*self.probEnemyDie(x, y, bomb_range, bomb_fuse, ex, ey-1)

		return ((self.c.ENEMY_MOVE_PROB*probMove) + ((1-self.c.ENEMY_MOVE_PROB)*probStay))

	def expectedEnemyBombProb(self, bomb):
		x = self.user.position[0]/self.c.TILE_SIZE
		y = self.user.position[1]/self.c.TILE_SIZE
		bomb_range = bomb.range
		bomb_fuse = bomb.fuse

		totalWeight = 0 
		for e in self.enemies:
			totalWeight += self.probEnemyDie(x, y, bomb_range, bomb_fuse, e.position[0]/self.c.TILE_SIZE, e.position[1]/self.c.TILE_SIZE)

		return totalWeight

	def expectedBombReward(self, bomb):
		brick_reward = 0.25
		enemy_reward = 1.0
		
		numBricks = self.expectedBombNumBricks(bomb)
		totalWeight = self.expectedEnemyBombProb(bomb)

		# print (self.user.position[0]/self.c.TILE_SIZE, self.user.position[1]/self.c.TILE_SIZE)
		# self.field.printBoard()
		# print (self.enemies[0].position[0]/self.c.TILE_SIZE, self.enemies[0].position[1]/self.c.TILE_SIZE)
		# print (numBricks, totalWeight)

		return (numBricks*brick_reward + totalWeight*enemy_reward)


		
		
