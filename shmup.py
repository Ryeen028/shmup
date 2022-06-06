import os
try:
    import pygame
    import random
    from imutils.video import VideoStream
    from tracker import get_pos
except ModuleNotFoundError:
    print("missing dependencies...")
    x = input("would you like to install dependencies? (y/n)? ")
    if x == 'y':
        os.system("pip install -r requirements.txt")
        os.system("python3 shmup.py")
        exit()
    else:
        print("run install_dependencies.py or see requirements.txt to resolve dependencies")
        exit()

# Frozen Jam by tgfcoder
# Art from Kenney.nl

USE_MOTION = True

greenLower = (29, 86, 6)
greenUpper = (64, 255, 255)
vs = VideoStream(src=0).start()

art_dir = os.path.join(os.path.dirname(__file__), 'art')
snd_dir = os.path.join(os.path.dirname(__file__), 'snd')

WIDTH = 480
HEIGHT = 600
FPS = 30

# initialize pygame and create window
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Shmup!")
clock = pygame.time.Clock()

# colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
PURPLE = (255, 0, 255)

SHIELD_BONUS = [20, 40]
POWERUP_TIME = 5000

# Load all game graphics
background = pygame.image.load(os.path.join(art_dir, "background"))
background = pygame.transform.scale(background, (480, 600))
background_rect = background.get_rect()

player_img = pygame.image.load(os.path.join(art_dir, "ship")).convert()
player_mini_img = pygame.transform.scale(player_img, (25, 19))
player_mini_img.set_colorkey(BLACK)
# meteor_img = pygame.image.load(os.path.join(art_dir, "meteor")).convert()
bullet_img_1 = pygame.image.load(os.path.join(art_dir, "laser_blue")).convert()
bullet_img_1 = pygame.transform.scale(bullet_img_1, (10, 30))
bullet_img_2 = pygame.image.load(os.path.join(art_dir, "laser_red")).convert()
bullet_img_2 = pygame.transform.scale(bullet_img_2, (10, 30))

meteor_images = []
invulnerable_meteor_images = []
explosion_anim = {}
explosion_anim['large'] = []
explosion_anim['small'] = []
images = os.listdir(art_dir)
for i in images:
	if "r_meteor" in i:
		meteor_images.append(pygame.image.load(os.path.join(art_dir, i)).convert())
	if i.startswith("regularExplosion"):
		img = pygame.image.load(os.path.join(art_dir, i)).convert()
		img.set_colorkey(BLACK)
		img_lg = pygame.transform.scale(img, (75, 75))
		explosion_anim['large'].append(img_lg)
		img_sm = pygame.transform.scale(img, (32, 32))
		explosion_anim['small'].append(img_sm)
	if "i_meteor" in i:
		invulnerable_meteor_images.append(pygame.image.load(os.path.join(art_dir, i)).convert())

powerup_images = {
	"shield": pygame.image.load(os.path.join(art_dir, "shield")).convert(),
	"gun": pygame.image.load(os.path.join(art_dir, "bolt")).convert(),
	"laser": pygame.image.load(os.path.join(art_dir, "star")).convert()
}

# Load all game sounds
shoot_sound = pygame.mixer.Sound(os.path.join(snd_dir, 'laser_sound'))
start_sound = pygame.mixer.Sound(os.path.join(snd_dir, 'start_sound'))
death_sound = pygame.mixer.Sound(os.path.join(snd_dir, 'death_sound'))
game_over_sound = pygame.mixer.Sound(os.path.join(snd_dir, 'game_over_sound'))

explosion_sounds = []
sounds = os.listdir(snd_dir)
for s in sounds:
	if "explosion" in s:
		explosion_sounds.append(pygame.mixer.Sound(os.path.join(snd_dir, s)))

pygame.mixer.music.load(os.path.join(snd_dir, 'music'))
pygame.mixer.music.set_volume(0.4)
pygame.mixer.music.play(loops=-1)

font_name = pygame.font.match_font('Comic Mono')
def draw_text(surf, text, size, x, y):
	font = pygame.font.Font(font_name, size)
	text_surface = font.render(text, True, WHITE)
	text_rect = text_surface.get_rect()
	text_rect.midtop = (x, y)
	surf.blit(text_surface, text_rect)

def new_mob():
	m = Mob()
	all_sprites.add(m)
	mobs.add(m)

def draw_shield_bar(surf, x, y, pct):
	if pct < 0:
		pct = 0
	BAR_LENGTH = 100
	BAR_HEIGHT = 10
	fill = (pct / 100) * BAR_LENGTH
	outline_rect = pygame.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
	fill_rect = pygame.Rect(x, y, fill, BAR_HEIGHT)
	pygame.draw.rect(surf, GREEN, fill_rect)
	pygame.draw.rect(surf, WHITE, outline_rect, 2)

def draw_lives(surf, x, y, lives, img):
	for i in range(lives):
		img_rect = img.get_rect()
		img_rect.x = x + 30 * i
		img_rect.y = y
		surf.blit(img, img_rect)


class Player(pygame.sprite.Sprite):
	max_shield = 100
	def __init__(self):
		pygame.sprite.Sprite.__init__(self)
		self.image = pygame.transform.scale(player_img, (50, 38))
		self.image.set_colorkey(BLACK)
		self.rect = self.image.get_rect()
		self.radius = 25
		self.rect.centerx = WIDTH / 2
		self.rect.bottom = HEIGHT - 10
		self.xspeed = 0
		self.shield = Player.max_shield
		self.shoot_delay = 444
		self.last_shot = pygame.time.get_ticks()
		self.lives = 3
		self.hidden = False
		self.hide_timer = pygame.time.get_ticks()
		self.power = 1
		self.shot_power = 0
		self.power_time = pygame.time.get_ticks()
		self.shot_power_time = pygame.time.get_ticks()
		self.last_update_timer = 0


	def update(self):
		now = pygame.time.get_ticks()
		a = self.power >= 2
		b = now - self.power_time > POWERUP_TIME
		if a and b:
			self.power -= 1
			self.power_time = now
		a = self.shot_power >= 1
		b = now - self.shot_power_time > POWERUP_TIME
		if a and b:
			self.shot_power -= 1
			self.shot_power_time = now
		# unhide if hidden
		if self.hidden and now - self.hide_timer > 1000:
			self.hidden = False
			self.rect.centerx = WIDTH / 2
			self.rect.bottom = HEIGHT - 10
		
		self.xspeed = 0
		keystate = pygame.key.get_pressed()
		if USE_MOTION:
			self.shoot()
			self.rect.x = get_pos()

		else:
			if keystate[pygame.K_LEFT]:
				self.xspeed = -10
			if keystate[pygame.K_RIGHT]:
				self.xspeed = 10
			if keystate[pygame.K_SPACE]:
				self.shoot()
			if self.rect.left <= 0:
				self.rect.left = 0
			if self.rect.right >= WIDTH:
				self.rect.right = WIDTH
			self.rect.x += self.xspeed

	def powerup(self):
		self.power += 1
		self.power_time = pygame.time.get_ticks()
	
	def shot_powerup(self):
		self.shot_power += 1
		self.shot_power_time = pygame.time.get_ticks()

	def shoot(self):
		now = pygame.time.get_ticks()
		if now - self.last_shot > self.shoot_delay:
			self.last_shot = now
			if self.power == 1:
				bullet = Bullet(self.rect.centerx, self.rect.top, self.shot_power)
				all_sprites.add(bullet)
				bullets.add(bullet)
				shoot_sound.play()
			elif self.power >= 2:
				bullet1 = Bullet(self.rect.left, self.rect.centery, self.shot_power)
				bullet2 = Bullet(self.rect.right, self.rect.centery, self.shot_power)
				all_sprites.add(bullet1)
				all_sprites.add(bullet2)
				bullets.add(bullet1)
				bullets.add(bullet2)
				shoot_sound.play()

	def hide(self):
		# hide the player temporarily
		self.hidden = True
		self.hide_timer = pygame.time.get_ticks()
		self.rect.center = (WIDTH * 5, HEIGHT * 5) 

class Mob(pygame.sprite.Sprite):
	def reset_position(self):
		self.rect.x = random.randint(0, WIDTH - self.rect.width)
		self.rect.y = random.randint(-150, -100)
		self.speedy = random.randint(6, 16)
		self.speedx = random.randrange(-4, 4)

	def __init__(self):
		pygame.sprite.Sprite.__init__(self)
		self.can_be_destroyed = random.random() < 0.7
		if self.can_be_destroyed:
			self.image_orig = random.choice(meteor_images)
		else:
			self.image_orig = random.choice(invulnerable_meteor_images)
		self.image_orig.set_colorkey(BLACK)
		size = random.randint(20, 80)
		self.image_orig = pygame.transform.scale(self.image_orig, (size, size))
		self.image = self.image_orig.copy()
		self.rect = self.image.get_rect()
		self.radius = int(self.rect.width * .85 / 2)
		self.reset_position()
		self.rot = 0
		self.rot_speed = random.randrange(-8, 8)
		self.last_update = pygame.time.get_ticks()

	def rotate(self):
		now = pygame.time.get_ticks()
		if now - self.last_update > 50:
			self.last_update = now
			self.rot = (self.rot + self.rot_speed) % 360
			new_image = pygame.transform.rotate(self.image_orig, self.rot)
			old_center = self.rect.center
			self.image = new_image
			self.rect = self.image.get_rect()
			self.rect.center = old_center

	def update(self):
		self.rotate()
		self.rect.y += self.speedy
		self.rect.x += self.speedx
		if self.rect.top > HEIGHT + 10 or self.rect.right < -10 or self.rect.left > WIDTH + 10:
			new_mob()
			self.kill()
			

class Bullet(pygame.sprite.Sprite):
	def __init__(self, x, y, power):
		pygame.sprite.Sprite.__init__(self)
		self.power = power
		if not self.power:
			self.image = bullet_img_1
		else:
			self.image = bullet_img_2
		self.image.set_colorkey(BLACK)
		self.rect = self.image.get_rect()
		self.rect.bottom = y
		self.rect.centerx = x
		self.speedy = -20
	
	def update(self):
		self.rect.y += self.speedy
		# kill if it moves off the screen
		if self.rect.bottom < 0:
			self.kill()

class Pow(pygame.sprite.Sprite):
	def __init__(self, center):
		pygame.sprite.Sprite.__init__(self)
		self.type = random.choice(list(powerup_images.keys()))
		self.image = powerup_images[self.type]
		self.image.set_colorkey(BLACK)
		self.rect = self.image.get_rect()
		self.rect.center = center
		self.speedy = 10
	
	def update(self):
		self.rect.y += self.speedy
		# kill if it moves off the screen
		if self.rect.top > HEIGHT:
			self.kill()

class Explosion(pygame.sprite.Sprite):
	def __init__(self, center, size):
		pygame.sprite.Sprite.__init__(self)
		self.size = size
		self.image = explosion_anim[self.size][0]
		self.rect = self.image.get_rect()
		self.rect.center = center
		self.frame = 0
		self.last_update = pygame.time.get_ticks()
		self.framerate = 50

	def update(self):
		now = pygame.time.get_ticks()
		if now - self.last_update > self.framerate:
			self.last_update = now
			self.frame += 1
			if self.frame == len(explosion_anim[self.size]):
				self.kill()
			else:
				center = self.rect.center
				self.image = explosion_anim[self.size][self.frame]
				self.rect = self.image.get_rect()
				self.rect.center = center

def show_go_screen():
	screen.blit(background, background_rect)
	draw_text(screen, "SHMUP!", 64, WIDTH / 2, HEIGHT / 4)
	draw_text(screen, "Arrow keys move, Space to fire", 22, WIDTH / 2, HEIGHT / 2)
	draw_text(screen, "Press a key to begin", 18, WIDTH / 2, HEIGHT * 3/4)
	pygame.display.flip()
	waiting = True
	while waiting:
		clock.tick(FPS)
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				exit()
			if event.type == pygame.KEYUP:
				waiting = False

# Game loop
game_over = True
running = True
while running:
	if game_over:
		get_pos()
		show_go_screen()
		start_sound.play()
		game_over = False
		all_sprites = pygame.sprite.Group()
		mobs = pygame.sprite.Group()
		bullets = pygame.sprite.Group()
		powerups = pygame.sprite.Group()
		player = Player()
		all_sprites.add(player)
		for i in range(8):
			new_mob()

		score = 0
		
	# keep loop running at the right speed
	clock.tick(FPS)

	# events
	for event in pygame.event.get():
		# closing the window
		if event.type == pygame.QUIT:
			running = False

	# update
	all_sprites.update()

	# check if a bullet hits
	hits = pygame.sprite.groupcollide(mobs, bullets, False, False)
	for hit in hits:
		score += 50 - hit.radius
		random.choice(explosion_sounds).play()
		expl = Explosion(hit.rect.center, 'large')
		all_sprites.add(expl)
		power = 0
		for b in hits[hit]:
			if b.power:
				power = 1
			else:
				b.kill()

		if hit.can_be_destroyed or power:
			hit.kill()
			if random.random() > 0.9:
				pow = Pow(hit.rect.center)
				all_sprites.add(pow)
				powerups.add(pow)
			
			new_mob()

	# check to see if a mob hit the player
	hits = pygame.sprite.spritecollide(player, mobs, True, pygame.sprite.collide_circle)
	for hit in hits:
		player.shield -= hit.radius * 2
		expl = Explosion(hit.rect.center, 'small')
		new_mob()
		if player.shield < 0:
			death_explosion = Explosion(player.rect.center, 'large')
			all_sprites.add(death_explosion)
			player.hide()
			while not player.hidden:
				for m in mobs:
					m.reset_position()
			
			player.lives -= 1
			player.shield = Player.max_shield
			if player.lives:
				death_sound.play()

    # check to see if player hit a powerup
	hits = pygame.sprite.spritecollide(player, powerups, True)
	for hit in hits:
		if hit.type == "shield":
			player.shield += random.randrange(*SHIELD_BONUS)
			if player.shield >= 100:
				player.shield = 100
		elif hit.type == "gun":
			player.powerup()
		elif hit.type == "laser":
			player.shot_powerup()
	
	if player.lives == 0 and not death_explosion.alive():
		game_over = True
		game_over_sound.play()

	# draw / render
	screen.fill(BLACK)
	screen.blit(background, (0, 0))
	all_sprites.draw(screen)
	draw_text(screen, str(score), 18, WIDTH/2, 10)
	draw_shield_bar(screen, 5, 5, player.shield)
	draw_lives(screen, WIDTH - 100, 5, player.lives, player_mini_img)
	# after drawing everything, flip the display
	pygame.display.flip()

pygame.quit()
