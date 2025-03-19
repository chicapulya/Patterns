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

# Абстрактный класс Prototype
class Prototype(ABC):
    @abstractmethod
    def clone(self):
        pass

# Singleton для управления ресурсами
class ResourceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_resources()
        return cls._instance

    def _load_resources(self):
        self.textures = {
            'cowboy': pygame.image.load('assets/Cowboy4_idle with gun_0.png'),
            'bandit': pygame.image.load('assets/pixel_skeleton_uno.png'),
            'eagle': pygame.image.load('assets/spr_enemy_boss_09_dead.png'),
            'booster': pygame.image.load('assets/exp-removebg-preview.png'),
            'hp': pygame.image.load('assets/hp-removebg-preview.png')
        }

    @staticmethod
    def get_instance():
        if ResourceManager._instance is None:
            ResourceManager()
        return ResourceManager._instance

# Абстрактная фабрика врагов с использованием Prototype
class EnemyFactory(ABC):
    @abstractmethod
    def create_enemy(self):
        pass

class BanditFactory(EnemyFactory):
    def __init__(self):
        self.prototype = Bandit(0, 0)

    def create_enemy(self, x):
        enemy = self.prototype.clone()
        enemy.x = x
        enemy.y = 0
        return enemy

class EagleFactory(EnemyFactory):
    def __init__(self):
        self.prototype = Eagle(0, 0)

    def create_enemy(self):
        enemy = self.prototype.clone()
        enemy.x = random.randint(0, WIDTH)
        enemy.y = 0
        return enemy

# Абстрактная фабрика бустеров с использованием Prototype
class BoosterFactory(ABC):
    @abstractmethod
    def create_booster(self, x, y):
        pass

class SpeedBoosterFactory(BoosterFactory):
    def __init__(self):
        self.prototype = Booster(0, 0)

    def create_booster(self, x, y):
        booster = self.prototype.clone()
        booster.x = x
        booster.y = y
        return booster

class HealFactory(BoosterFactory):
    def __init__(self):
        self.prototype = Heal(0, 0)

    def create_booster(self, x, y):
        booster = self.prototype.clone()
        booster.x = x
        booster.y = y
        return booster

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

# Класс бандита с реализацией Prototype
class Bandit(Entity, Prototype):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['bandit']
        self.hp = 2
        self.base_speed = 1
        self.max_speed = 3

    def clone(self):
        return Bandit(self.x, self.y)

    def move(self, time):
        speed_increase = min(math.log1p(time / 60) * 0.25, self.max_speed - self.base_speed)
        self.speed = self.base_speed + speed_increase
        self.y += self.speed
        if random.random() < 0.01:
            self.x += random.choice([-self.speed, self.speed])
        self.update_rect()

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))

# Класс орла с реализацией Prototype
class Eagle(Entity, Prototype):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['eagle']
        self.hp = 1
        self.angle = 0
        self.shoot_timer = random.randint(30, 60)
        self.base_speed = 1
        self.max_speed = 3

    def clone(self):
        return Eagle(self.x, self.y)

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

# Класс бустера с реализацией Prototype
class Booster(Entity, Prototype):
    def __init__(self, x, y):
        super().__init__(x, y)
        original_texture = ResourceManager().textures['booster']
        self.texture = pygame.transform.scale(original_texture, (16, 16))
        self.rect = self.texture.get_rect(topleft=(x, y))
        self.speed = 3
        self.boost_value = 5
        self.duration = 300

    def clone(self):
        return Booster(self.x, self.y)

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
        screen.blit(self.texture, (self.x, self.y))

# Класс лечения с реализацией Prototype
class Heal(Entity, Prototype):
    def __init__(self, x, y):
        super().__init__(x, y)
        original_texture = ResourceManager().textures['hp']
        self.texture = pygame.transform.scale(original_texture, (32, 16))
        self.rect = self.texture.get_rect(topleft=(x, y))
        self.speed = 3
        self.heal_value = 1

    def clone(self):
        return Heal(self.x, self.y)

    def move(self):
        if self.y < HEIGHT - 64:
            self.y += self.speed
            self.update_rect()

    def apply(self, cowboy):
        if cowboy.hp < cowboy.max_hp:
            cowboy.hp = min(cowboy.max_hp, cowboy.hp + self.heal_value)

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))

# Builder и Director для создания игрового состояния
class GameStateBuilder:
    def __init__(self):
        self.game_state = {}

    def set_cowboy(self):
        self.game_state['cowboy'] = Cowboy(WIDTH // 2, HEIGHT - 64)
        return self

    def set_enemies(self):
        self.game_state['enemies'] = []
        return self

    def set_boosters(self):
        self.game_state['boosters'] = []
        return self

    def set_eagle_bullets(self):
        self.game_state['eagle_bullets'] = []
        return self

    def set_timers(self):
        self.game_state['spawn_timer'] = 0
        self.game_state['score'] = 0
        self.game_state['time'] = 0
        self.game_state['wave_phase'] = 0
        return self

    def set_game_over(self):
        self.game_state['game_over'] = False
        return self

    def build(self):
        return self.game_state

class GameDirector:
    def __init__(self, builder):
        self.builder = builder

    def construct_game_state(self):
        return (self.builder
                .set_cowboy()
                .set_enemies()
                .set_boosters()
                .set_eagle_bullets()
                .set_timers()
                .set_game_over()
                .build())

# Основной игровой цикл
def main():
    title_font = pygame.font.SysFont("Arial", 48, bold=True)
    text_font = pygame.font.SysFont("Arial", 24, bold=True)

    hp_texture = pygame.transform.scale(ResourceManager().textures['hp'], (40, 20))

    builder = GameStateBuilder()
    director = GameDirector(builder)

    def reset_game():
        nonlocal game_state
        game_state = director.construct_game_state()

    game_state = director.construct_game_state()

    bandit_factory = BanditFactory()
    eagle_factory = EagleFactory()
    speed_booster_factory = SpeedBoosterFactory()
    heal_factory = HealFactory()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and game_state['game_over']:
                mouse_pos = pygame.mouse.get_pos()
                if restart_button.collidepoint(mouse_pos):
                    reset_game()

        if not game_state['game_over']:
            keys = pygame.key.get_pressed()
            game_state['cowboy'].move(keys)
            if keys[pygame.K_SPACE]:
                game_state['cowboy'].shoot()

            game_state['cowboy'].update_boost()

            game_state['spawn_timer'] -= 1
            if game_state['spawn_timer'] <= 0:
                spawn_interval = max(30, 60 - (game_state['time'] // 60))
                game_state['spawn_timer'] = spawn_interval

                game_state['wave_phase'] += 0.0005
                wave_factor = (math.sin(game_state['wave_phase']) + 1) / 2

                if random.random() < 0.6:
                    max_bandits = 4
                    min_bandits = 1
                    bandit_count = min_bandits + int(wave_factor * (max_bandits - min_bandits))
                    segment_width = WIDTH // max_bandits
                    for i in range(bandit_count):
                        base_x = i * segment_width + segment_width // 2
                        spawn_x = base_x + random.randint(-segment_width // 4, segment_width // 4)
                        spawn_x = max(0, min(spawn_x, WIDTH - 32))
                        game_state['enemies'].append(bandit_factory.create_enemy(spawn_x))
                else:
                    game_state['enemies'].append(eagle_factory.create_enemy())

            game_state['time'] += 1

            for bullet in game_state['cowboy'].bullets[:]:
                bullet.move()
                if bullet.y < 0:
                    game_state['cowboy'].bullets.remove(bullet)
                else:
                    for enemy in game_state['enemies'][:]:
                        if bullet.rect.colliderect(enemy.rect):
                            enemy.hp -= 1 * game_state['cowboy'].damage_boost
                            game_state['cowboy'].bullets.remove(bullet)
                            if enemy.hp <= 0:
                                game_state['enemies'].remove(enemy)
                                game_state['score'] += 10
                                base_drop_chance = 0.1
                                time_factor = min(0.4, (game_state['time'] / 60) * 0.01)
                                drop_chance = base_drop_chance + time_factor
                                if random.random() < drop_chance:
                                    if random.random() < 0.5:
                                        game_state['boosters'].append(speed_booster_factory.create_booster(enemy.x, enemy.y))
                                    else:
                                        game_state['boosters'].append(heal_factory.create_booster(enemy.x, enemy.y))
                            break

            for enemy in game_state['enemies'][:]:
                enemy.move(game_state['time'])
                if isinstance(enemy, Eagle):
                    bullet = enemy.shoot()
                    if bullet:
                        game_state['eagle_bullets'].append(bullet)
                if enemy.rect.colliderect(game_state['cowboy'].rect):
                    game_state['cowboy'].hp -= 1
                    game_state['enemies'].remove(enemy)
                    if game_state['cowboy'].hp <= 0:
                        game_state['game_over'] = True

            for bullet in game_state['eagle_bullets'][:]:
                bullet.move()
                if bullet.y > HEIGHT:
                    game_state['eagle_bullets'].remove(bullet)
                elif bullet.rect.colliderect(game_state['cowboy'].rect):
                    game_state['cowboy'].hp -= 1
                    game_state['eagle_bullets'].remove(bullet)
                    if game_state['cowboy'].hp <= 0:
                        game_state['game_over'] = True

            for booster in game_state['boosters'][:]:
                booster.move()
                if game_state['cowboy'].rect.colliderect(booster.rect):
                    booster.apply(game_state['cowboy'])
                    game_state['boosters'].remove(booster)
                elif booster.y >= HEIGHT - 64:
                    game_state['boosters'].remove(booster)

            screen.fill((135, 206, 235))

            score_text = text_font.render(f"Score: {game_state['score']}", True, (0, 0, 0))
            time_text = text_font.render(f"Time: {game_state['time'] // 60}", True, (0, 0, 0))
            boost_text = text_font.render(f"Boost: {game_state['cowboy'].boost_duration // 60}", True,
                                        (0, 255, 0)) if game_state['cowboy'].boost_active else text_font.render("Boost: 0", True, (0, 0, 0))
            screen.blit(score_text, (10, 5))
            screen.blit(time_text, (10, 30))
            screen.blit(boost_text, (10, 55))

            for i in range(game_state['cowboy'].hp):
                screen.blit(hp_texture, (10 + i * 45, 85))

            game_state['cowboy'].draw(screen)
            for bullet in game_state['cowboy'].bullets:
                bullet.draw(screen)
            for enemy in game_state['enemies']:
                enemy.draw(screen)
            for booster in game_state['boosters']:
                booster.draw(screen)
            for bullet in game_state['eagle_bullets']:
                bullet.draw(screen)

        if game_state['game_over']:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((50, 50, 50))
            screen.blit(overlay, (0, 0))

            game_over_text = title_font.render("Game Over", True, (255, 0, 0))
            game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
            screen.blit(game_over_text, game_over_rect)

            score_display = text_font.render(f"Final Score: {game_state['score']}", True, (255, 255, 255))
            score_rect = score_display.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(score_display, score_rect)

            restart_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 40, 200, 50)
            pygame.draw.rect(screen, (0, 255, 0), restart_button)
            pygame.draw.rect(screen, (0, 0, 0), restart_button, 2)
            restart_text = text_font.render("Restart", True, (0, 0, 0))
            restart_rect = restart_text.get_rect(center=restart_button.center)
            screen.blit(restart_text, restart_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()