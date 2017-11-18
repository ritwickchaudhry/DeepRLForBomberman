class Config(object):
	# RFCT - Design flaw, didn't think of it earlier, but only 9 tiles possible with current configuration =/
	GROUND = 0
	WALL = 1
	BRICK = 2
	BOMB_UP = 3
	POWER_UP = 4
	LIFE_UP = 5
	TIME_UP = 6
	ENEMY_MOVE_PROB = 0.2
	FPS = 10
	WIDTH = 840
	HEIGHT = 690
	TILE_SIZE = 40
	IMAGE_PATH = "resources/images/"
	AUDIO_PATH = "resources/sounds/"
	HIGHSCORES_PATH = "resources/highscores.txt"
	SINGLE = 'Single'
	MULTI = 'Multi'
	MAX_ENEMY_SPRITES = 9
	LOCALHOST = False
