import pygame
import random
import math
from abc import ABC, abstractmethod

# Инициализация Pygame
pygame.init()

# Константы
WIDTH, HEIGHT = 800, 600
FPS = 60

# Экран
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cowboy Shooter")
clock = pygame.time.Clock()

# Singleton для управления ресурсами
class ResourceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.textures = {
                'cowboy': pygame.image.load('assets/Cowboy4_idle with gun_0.png'),
                'bandit': pygame.image.load('assets/pixel_skeleton_uno.png'),
                'eagle': pygame.image.load('assets/spr_enemy_boss_09_dead.png')
            }
        return cls._instance

# Абстрактная фабрика врагов
class EnemyFactory(ABC):
    @abstractmethod
    def create_enemy(self):
        pass

class BanditFactory(EnemyFactory):
    def create_enemy(self, x):
        return Bandit(x, 0)

class EagleFactory(EnemyFactory):
    def create_enemy(self):
        return Eagle(random.randint(0, WIDTH), 0)

# Абстрактная фабрика бустеров
class BoosterFactory(ABC):
    @abstractmethod
    def create_booster(self, x, y):
        pass

class SpeedBoosterFactory(BoosterFactory):
    def create_booster(self, x, y):
        return Booster(x, y)

class HealFactory(BoosterFactory):
    def create_booster(self, x, y):
        return Heal(x, y)

# Обычная фабрика для пуль
class BulletFactory:
    @staticmethod
    def create_bullet(bullet_type, x, y):
        if bullet_type == "player":
            return Bullet(x, y)
        elif bullet_type == "eagle":
            return EagleBullet(x, y)
        else:
            raise ValueError("Unknown bullet type")

# Базовый класс сущности
class Entity:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 2
        self.rect = pygame.Rect(x, y, 32, 32)

    def update_rect(self):
        self.rect.x = self.x
        self.rect.y = self.y

    def move(self):
        pass

    def draw(self):
        pass

# Класс игрока
class Cowboy(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['cowboy']
        self.rect = pygame.Rect(x, y, 32, 32)
        self.bullets = []
        self.shoot_timer = 0
        self.speed_boost = 1.0
        self.damage_boost = 1.0
        self.hp = 3
        self.max_hp = 5
        self.base_shoot_cooldown = 20
        self.shoot_cooldown = self.base_shoot_cooldown
        self.boost_duration = 0
        self.boost_active = False
        self.height = self.texture.get_height()

    def move(self, keys):
        if keys[pygame.K_LEFT]:
            self.x -= self.speed * self.speed_boost
        if keys[pygame.K_RIGHT]:
            self.x += self.speed * self.speed_boost
        if keys[pygame.K_UP]:
            self.y -= self.speed * self.speed_boost
        if keys[pygame.K_DOWN]:
            self.y += self.speed * self.speed_boost
        self.x = max(0, min(self.x, WIDTH - self.rect.width))
        self.y = max(0, min(self.y, HEIGHT - self.height))
        self.update_rect()

    def shoot(self):
        if self.shoot_timer <= 0:
            bullet = BulletFactory.create_bullet("player", self.x + 16, self.y)
            self.bullets.append(bullet)
            self.shoot_timer = self.shoot_cooldown
        self.shoot_timer -= 1

    def update_boost(self):
        if self.boost_active:
            self.boost_duration -= 1
            if self.boost_duration <= 0:
                self.shoot_cooldown = self.base_shoot_cooldown
                self.boost_active = False

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))

# Класс пули игрока
class Bullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 5
        self.rect = pygame.Rect(x, y, 4, 8)

    def move(self):
        self.y -= self.speed
        self.update_rect()

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 255, 0), (self.x, self.y, 4, 8))

# Класс пули орла
class EagleBullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 3
        self.rect = pygame.Rect(x, y, 8, 4)

    def move(self):
        self.y += self.speed
        self.update_rect()

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, 8, 4))

# Класс бандита
class Bandit(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['bandit']
        self.hp = 2
        self.base_speed = 1
        self.max_speed = 3

    def move(self, time):
        speed_increase = min(math.log1p(time / 60) * 0.25, self.max_speed - self.base_speed)
        self.speed = self.base_speed + speed_increase
        self.y += self.speed
        if random.random() < 0.01:
            self.x += random.choice([-self.speed, self.speed])
        self.update_rect()

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))

# Класс орла
class Eagle(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['eagle']
        self.hp = 1
        self.angle = 0
        self.shoot_timer = random.randint(30, 60)
        self.base_speed = 1
        self.max_speed = 3

    def move(self, time):
        speed_increase = min(math.log1p(time / 60) * 0.25, self.max_speed - self.base_speed)
        self.speed = self.base_speed + speed_increase
        self.y += math.sin(self.angle) * self.speed
        self.x += self.speed
        self.angle += 0.1
        self.update_rect()

    def shoot(self):
        if self.shoot_timer <= 0:
            self.shoot_timer = random.randint(30, 60)
            return BulletFactory.create_bullet("eagle", self.x + 16, self.y + 32)
        self.shoot_timer -= 1
        return None

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))

# Класс бустера (ускорение стрельбы)
class Booster(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.rect = pygame.Rect(x, y, 16, 16)
        self.speed = 3
        self.boost_value = 5
        self.duration = 300

    def move(self):
        if self.y < HEIGHT - 64:
            self.y += self.speed
            self.update_rect()

    def apply(self, cowboy):
        if cowboy.boost_active:
            cowboy.boost_duration += self.duration
        else:
            cowboy.boost_duration = self.duration
            cowboy.shoot_cooldown = max(5, cowboy.base_shoot_cooldown - self.boost_value)
            cowboy.boost_active = True

    def draw(self, screen):
        pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y, 16, 16))

# Класс лечения (восстановление HP)
class Heal(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.rect = pygame.Rect(x, y, 16, 16)
        self.speed = 3
        self.heal_value = 1

    def move(self):
        if self.y < HEIGHT - 64:
            self.y += self.speed
            self.update_rect()

    def apply(self, cowboy):
        if cowboy.hp < cowboy.max_hp:
            cowboy.hp = min(cowboy.max_hp, cowboy.hp + self.heal_value)

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, 16, 16))

# Основной игровой цикл
def main():
    font = pygame.font.Font(None, 36)
    game_over = False

    def reset_game():
        nonlocal cowboy, enemies, boosters, spawn_timer, score, time, game_over, eagle_bullets, wave_phase
        cowboy = Cowboy(WIDTH // 2, HEIGHT - 64)
        enemies = []
        boosters = []
        spawn_timer = 0
        score = 0
        time = 0
        game_over = False
        eagle_bullets = []
        wave_phase = 0

    cowboy = Cowboy(WIDTH // 2, HEIGHT - 64)
    enemies = []
    boosters = []
    eagle_bullets = []
    spawn_timer = 0
    score = 0
    time = 0
    wave_phase = 0

    bandit_factory = BanditFactory()
    eagle_factory = EagleFactory()
    speed_booster_factory = SpeedBoosterFactory()
    heal_factory = HealFactory()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and game_over:
                mouse_pos = pygame.mouse.get_pos()
                if restart_button.collidepoint(mouse_pos):
                    reset_game()

        if not game_over:
            keys = pygame.key.get_pressed()
            cowboy.move(keys)
            if keys[pygame.K_SPACE]:
                cowboy.shoot()

            cowboy.update_boost()

            spawn_timer -= 1
            if spawn_timer <= 0:
                spawn_interval = max(30, 60 - (time // 60))
                spawn_timer = spawn_interval

                wave_phase += 0.0005
                wave_factor = (math.sin(wave_phase) + 1) / 2

                if random.random() < 0.6:
                    max_bandits = 4
                    min_bandits = 1
                    bandit_count = min_bandits + int(wave_factor * (max_bandits - min_bandits))
                    segment_width = WIDTH // max_bandits
                    for i in range(bandit_count):
                        base_x = i * segment_width + segment_width // 2
                        spawn_x = base_x + random.randint(-segment_width // 4, segment_width // 4)
                        spawn_x = max(0, min(spawn_x, WIDTH - 32))
                        enemies.append(bandit_factory.create_enemy(spawn_x))
                else:
                    enemies.append(eagle_factory.create_enemy())

            time += 1

            for bullet in cowboy.bullets[:]:
                bullet.move()
                if bullet.y < 0:
                    cowboy.bullets.remove(bullet)
                else:
                    for enemy in enemies[:]:
                        if bullet.rect.colliderect(enemy.rect):
                            enemy.hp -= 1 * cowboy.damage_boost
                            cowboy.bullets.remove(bullet)
                            if enemy.hp <= 0:
                                enemies.remove(enemy)
                                score += 10
                                base_drop_chance = 0.1
                                time_factor = min(0.4, (time / 60) * 0.01)
                                drop_chance = base_drop_chance + time_factor
                                if random.random() < drop_chance:
                                    if random.random() < 0.5:
                                        boosters.append(speed_booster_factory.create_booster(enemy.x, enemy.y))
                                    else:
                                        boosters.append(heal_factory.create_booster(enemy.x, enemy.y))
                            break

            for enemy in enemies[:]:
                enemy.move(time)
                if isinstance(enemy, Eagle):
                    bullet = enemy.shoot()
                    if bullet:
                        eagle_bullets.append(bullet)
                if enemy.rect.colliderect(cowboy.rect):
                    cowboy.hp -= 1
                    enemies.remove(enemy)
                    if cowboy.hp <= 0:
                        game_over = True

            for bullet in eagle_bullets[:]:
                bullet.move()
                if bullet.y > HEIGHT:
                    eagle_bullets.remove(bullet)
                elif bullet.rect.colliderect(cowboy.rect):
                    cowboy.hp -= 1
                    eagle_bullets.remove(bullet)
                    if cowboy.hp <= 0:
                        game_over = True

            for booster in boosters[:]:
                booster.move()
                if cowboy.rect.colliderect(booster.rect):
                    booster.apply(cowboy)
                    boosters.remove(booster)
                elif booster.y >= HEIGHT - 64:
                    boosters.remove(booster)

            screen.fill((135, 206, 235))

            for i in range(cowboy.hp):
                pygame.draw.rect(screen, (255, 0, 0), (10 + i * 40, 70, 30, 30))

            score_text = font.render(f"Score: {score}", True, (0, 0, 0))
            time_text = font.render(f"Time: {time // 60}", True, (0, 0, 0))
            boost_text = font.render(f"Boost: {cowboy.boost_duration // 60}", True,
                                     (0, 255, 0)) if cowboy.boost_active else font.render("Boost: 0", True, (0, 0, 0))
            wave_text = font.render(f"Wave: {wave_factor:.2f}", True, (0, 0, 0))
            screen.blit(score_text, (10, 10))
            screen.blit(time_text, (10, 40))
            screen.blit(boost_text, (10, 100))
            screen.blit(wave_text, (10, 130))

            cowboy.draw(screen)
            for bullet in cowboy.bullets:
                bullet.draw(screen)
            for enemy in enemies:
                enemy.draw(screen)
            for booster in boosters:
                booster.draw(screen)
            for bullet in eagle_bullets:
                bullet.draw(screen)

        if game_over:
            game_over_text = font.render("Game Over", True, (255, 0, 0))
            score_display = font.render(f"Final Score: {score}", True, (0, 0, 0))
            restart_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50)

            screen.blit(game_over_text, (WIDTH // 2 - 80, HEIGHT // 2 - 50))
            screen.blit(score_display, (WIDTH // 2 - 80, HEIGHT // 2))
            pygame.draw.rect(screen, (0, 255, 0), restart_button)
            restart_text = font.render("Restart", True, (0, 0, 0))
            screen.blit(restart_text, (WIDTH // 2 - 50, HEIGHT // 2 + 60))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()