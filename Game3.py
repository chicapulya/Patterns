import pygame
import random
import math
from abc import ABC, abstractmethod
import copy

# Инициализация Pygame
pygame.init()

# Константы
WIDTH, HEIGHT = 800, 600
FPS = 60

# Экран
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cowboy Shooter")
clock = pygame.time.Clock()


# Strategy Interface for Enemy Movement
class MovementStrategy(ABC):
    @abstractmethod
    def move(self, entity, time=None):
        pass


# Concrete Strategy for Linear Movement (used by Bandit)
class LinearMovementStrategy(MovementStrategy):
    def move(self, entity, time=None):
        if time:
            speed_increase = min(math.log1p(time / 60) * 0.25, entity.max_speed - entity.base_speed)
            entity.speed = entity.base_speed + speed_increase
        entity.y += entity.speed
        if random.random() < 0.01:
            entity.x += random.choice([-entity.speed, entity.speed])
        entity.update_rect()


# Concrete Strategy for Sinusoidal Movement (used by Eagle)
class SinusoidalMovementStrategy(MovementStrategy):
    def move(self, entity, time=None):
        if time:
            speed_increase = min(math.log1p(time / 60) * 0.25, entity.max_speed - entity.base_speed)
            entity.speed = entity.base_speed + speed_increase
        entity.y += math.sin(entity.angle) * entity.speed
        entity.x += entity.speed
        entity.angle += 0.1
        entity.update_rect()


# Concrete Strategy for ZigZag Movement (used by Bandit with 30% chance)
class ZigZagMovementStrategy(MovementStrategy):
    def move(self, entity, time=None):
        if time:
            speed_increase = min(math.log1p(time / 60) * 0.25, entity.max_speed - entity.base_speed)
            entity.speed = entity.base_speed + speed_increase
        entity.y += entity.speed
        entity.x += math.cos(entity.angle) * entity.speed * 1
        entity.angle += 0.0333  # Reduced from 0.1 to 0.0333 to make horizontal deviations 3 times longer
        entity.update_rect()


# Mediator Interface
class GameObjectMediator(ABC):
    @abstractmethod
    def update_objects(self, facade, keys, wasd_controls):
        pass

    @abstractmethod
    def handle_collisions(self, facade):
        pass


# Concrete Mediator
class GameObjectMediatorImpl(GameObjectMediator):
    def update_objects(self, facade, keys, wasd_controls):
        cowboy = facade.game_state['cowboy']

        # Handle cowboy movement
        if keys[pygame.K_LEFT]:
            cowboy.execute_command(MoveCommand(cowboy, -1, 0))
        if keys[pygame.K_RIGHT]:
            cowboy.execute_command(MoveCommand(cowboy, 1, 0))
        if keys[pygame.K_UP]:
            cowboy.execute_command(MoveCommand(cowboy, 0, -1))
        if keys[pygame.K_DOWN]:
            cowboy.execute_command(MoveCommand(cowboy, 0, 1))

        if wasd_controls['move_x'] != 0 or wasd_controls['move_y'] != 0:
            cowboy.execute_command(MoveCommand(cowboy, wasd_controls['move_x'], wasd_controls['move_y']))

        if keys[pygame.K_SPACE]:
            cowboy.execute_command(ShootCommand(cowboy))

        if keys[pygame.K_z]:
            cowboy.undo_last_command()

        cowboy.update_boost()

        # Handle spawning
        facade.game_state['spawn_timer'] -= 1
        if facade.game_state['spawn_timer'] <= 0:
            spawn_interval = max(30, 60 - (facade.game_state['time'] // 60))
            facade.game_state['spawn_timer'] = spawn_interval

            facade.game_state['wave_phase'] += 0.0005
            wave_factor = (math.sin(facade.game_state['wave_phase']) + 1) / 2

            wave_duration = 30 * 60
            facade.game_state['current_wave'] = (facade.game_state['time'] // wave_duration) % len(
                facade.game_state['waves'])
            current_wave = facade.game_state['waves'][facade.game_state['current_wave']]

            if random.random() < 0.6:
                max_bandits = 4
                min_bandits = 1
                bandit_count = min_bandits + int(wave_factor * (max_bandits - min_bandits))
                segment_width = WIDTH // max_bandits
                for i in range(bandit_count):
                    base_x = i * segment_width + segment_width // 2
                    spawn_x = base_x + random.randint(-segment_width // 4, segment_width // 4)
                    spawn_x = max(0, min(spawn_x, WIDTH - 32))
                    enemy = facade.bandit_factory.create_enemy(spawn_x)
                    current_wave.add(enemy)
            else:
                enemy = facade.eagle_factory.create_enemy()
                current_wave.add(enemy)

        facade.game_state['time'] += 1

        # Update all game objects
        for bullet in facade.game_state['cowboy'].bullets:
            bullet.update()
        facade.game_state['enemies'].update()
        for bullet in facade.game_state['eagle_bullets']:
            bullet.update()
        facade.game_state['boosters'].update()
        for notification in facade.notifications:
            notification.update()

    def handle_collisions(self, facade):
        cowboy = facade.game_state['cowboy']

        # Handle cowboy bullets
        for bullet in cowboy.bullets[:]:
            if bullet.y < 0:
                cowboy.bullets.remove(bullet)
                continue
            for wave in facade.game_state['enemies'].children[:]:
                for enemy in wave.children[:]:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.hp -= 1 * cowboy.damage_boost
                        cowboy.bullets.remove(bullet)
                        if enemy.hp <= 0:
                            wave.remove(enemy)
                            facade.notify("enemy_defeated", {"score_value": 10})
                            base_drop_chance = 0.1
                            time_factor = min(0.4, (facade.game_state['time'] / 60) * 0.01)
                            drop_chance = base_drop_chance + time_factor
                            if random.random() < drop_chance:
                                if random.random() < 0.5:
                                    booster = facade.speed_booster_factory.create_booster(enemy.x, enemy.y)
                                    facade.game_state['boosters'].add(booster)
                                else:
                                    booster = facade.heal_factory.create_booster(enemy.x, enemy.y)
                                    facade.game_state['boosters'].add(booster)
                        break

        # Handle enemy interactions
        for wave in facade.game_state['enemies'].children[:]:
            for enemy in wave.children[:]:
                if isinstance(enemy, Eagle):
                    bullet = enemy.shoot()
                    if bullet:
                        facade.game_state['eagle_bullets'].append(bullet)
                if enemy.rect.colliderect(cowboy.rect):
                    cowboy.set_health(cowboy.hp - 1)
                    wave.remove(enemy)

        # Handle eagle bullets
        for bullet in facade.game_state['eagle_bullets'][:]:
            if bullet.y > HEIGHT:
                facade.game_state['eagle_bullets'].remove(bullet)
            elif bullet.rect.colliderect(cowboy.rect):
                cowboy.set_health(cowboy.hp - 1)
                facade.game_state['eagle_bullets'].remove(bullet)

        # Handle boosters
        for booster in facade.game_state['boosters'].children[:]:
            if cowboy.rect.colliderect(booster.rect):
                booster.apply(cowboy)
                facade.game_state['boosters'].remove(booster)
            elif booster.y >= HEIGHT - 64:
                facade.game_state['boosters'].remove(booster)

        # Handle notifications
        for notification in facade.notifications[:]:
            if notification.duration <= 0:
                facade.notifications.remove(notification)


# Класс для уведомлений
class Notification:
    def __init__(self, text, x, y, duration, color=(255, 255, 255)):
        self.text = text
        self.x = x
        self.y = y
        self.duration = duration
        self.color = color
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.alpha = 255

    def update(self):
        self.duration -= 1
        self.y -= 0.5
        self.alpha = max(0, self.alpha - 255 / 60)

    def draw(self, screen):
        if self.duration > 0:
            surface = self.font.render(self.text, True, self.color)
            surface.set_alpha(self.alpha)
            screen.blit(surface, (self.x, self.y))


# Абстрактный класс Observer
class Observer(ABC):
    @abstractmethod
    def update(self, event_type, data):
        pass


# Абстрактный класс Subject
class Subject(ABC):
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event_type, data):
        for observer in self._observers:
            observer.update(event_type, data)


# Конкретные наблюдатели
class ScoreObserver(Observer):
    def __init__(self, game_state):
        self.game_state = game_state

    def update(self, event_type, data):
        if event_type == "enemy_defeated":
            self.game_state['score'] += data['score_value']


class UIObserver(Observer):
    def __init__(self, facade):
        self.facade = facade

    def update(self, event_type, data):
        if event_type == "health_changed":
            health = data['health']
            text = f"Health: {health}" if health > 0 else "Game Over!"
            color = (255, 0, 0) if health < self.facade.game_state['cowboy'].hp else (0, 255, 0)
            self.facade.add_notification(text, self.facade.game_state['cowboy'].x,
                                         self.facade.game_state['cowboy'].y - 20, 60, color)
        elif event_type == "booster_collected":
            self.facade.add_notification("Booster Collected!", self.facade.game_state['cowboy'].x,
                                         self.facade.game_state['cowboy'].y - 20, 60, (0, 255, 0))


class GameStateObserver(Observer):
    def __init__(self, facade):
        self.facade = facade

    def update(self, event_type, data):
        if event_type == "health_changed" and data['health'] <= 0:
            self.facade.change_state(GameOverState(self.facade))


# Абстрактный класс для игровых состояний
class GameState(ABC):
    @abstractmethod
    def handle_events(self, facade):
        pass

    @abstractmethod
    def update(self, facade):
        pass

    @abstractmethod
    def draw(self, facade, screen):
        pass


# Состояние меню
class MenuState(GameState):
    def __init__(self):
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.start_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 50)

    def handle_events(self, facade):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if self.start_button.collidepoint(mouse_pos):
                    facade.start_new_game()
                    facade.change_state(PlayingState())
        return True

    def update(self, facade):
        pass

    def draw(self, facade, screen):
        screen.fill((135, 206, 235))
        title_text = self.title_font.render("Cowboy Shooter", True, (0, 0, 0))
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        screen.blit(title_text, title_rect)

        pygame.draw.rect(screen, (0, 255, 0), self.start_button)
        pygame.draw.rect(screen, (0, 0, 0), self.start_button, 2)
        start_text = self.text_font.render("Start", True, (0, 0, 0))
        start_rect = start_text.get_rect(center=self.start_button.center)
        screen.blit(start_text, start_rect)


# Состояние игры
class PlayingState(GameState):
    def __init__(self):
        self.pause_button = pygame.Rect(WIDTH - 110, 10, 100, 40)
        self.text_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.mediator = GameObjectMediatorImpl()

    def handle_events(self, facade):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if self.pause_button.collidepoint(mouse_pos):
                    facade.change_state(PauseState())
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    facade.change_state(PauseState())
        return True

    def update(self, facade):
        keys = pygame.key.get_pressed()
        wasd_controls = facade.wasd_input.get_controls()
        self.mediator.update_objects(facade, keys, wasd_controls)
        self.mediator.handle_collisions(facade)

    def draw(self, facade, screen):
        screen.fill((135, 206, 235))

        score_text = facade.text_font.render(f"Score: {facade.game_state['score']}", True, (0, 0, 0))
        time_text = facade.text_font.render(f"Time: {facade.game_state['time'] // 60}", True, (0, 0, 0))
        boost_text = facade.text_font.render(f"Boost: {facade.game_state['cowboy'].boost_duration // 60}", True,
                                             (0, 255, 0)) if facade.game_state[
            'cowboy'].boost_active else facade.text_font.render("Boost: 0", True, (0, 0, 0))
        wave_text = facade.text_font.render(f"Wave: {facade.game_state['current_wave'] + 1}", True, (0, 0, 255))
        screen.blit(score_text, (10, 5))
        screen.blit(time_text, (10, 30))
        screen.blit(boost_text, (10, 55))
        screen.blit(wave_text, (10, 80))

        for i in range(facade.game_state['cowboy'].hp):
            screen.blit(facade.hp_texture, (10 + i * 45, 105))

        facade.game_state['cowboy'].draw(screen)
        for bullet in facade.game_state['cowboy'].bullets:
            bullet.draw(screen)
        facade.game_state['enemies'].draw(screen)
        facade.game_state['boosters'].draw(screen)
        for bullet in facade.game_state['eagle_bullets']:
            bullet.draw(screen)

        for notification in facade.notifications:
            notification.draw(screen)

        pygame.draw.rect(screen, (255, 165, 0), self.pause_button)
        pygame.draw.rect(screen, (0, 0, 0), self.pause_button, 2)
        pause_text = self.text_font.render("Pause", True, (0, 0, 0))
        pause_rect = pause_text.get_rect(center=self.pause_button.center)
        screen.blit(pause_text, pause_rect)


# Состояние паузы
class PauseState(GameState):
    def __init__(self):
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.resume_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 50)

    def handle_events(self, facade):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if self.resume_button.collidepoint(mouse_pos):
                    facade.change_state(PlayingState())
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    facade.change_state(PlayingState())
        return True

    def update(self, facade):
        pass

    def draw(self, facade, screen):
        screen.fill((135, 206, 235))
        score_text = facade.text_font.render(f"Score: {facade.game_state['score']}", True, (0, 0, 0))
        time_text = facade.text_font.render(f"Time: {facade.game_state['time'] // 60}", True, (0, 0, 0))
        boost_text = facade.text_font.render(f"Boost: {facade.game_state['cowboy'].boost_duration // 60}", True,
                                             (0, 255, 0)) if facade.game_state[
            'cowboy'].boost_active else facade.text_font.render("Boost: 0", True, (0, 0, 0))
        wave_text = facade.text_font.render(f"Wave: {facade.game_state['current_wave'] + 1}", True, (0, 0, 255))
        screen.blit(score_text, (10, 5))
        screen.blit(time_text, (10, 30))
        screen.blit(boost_text, (10, 55))
        screen.blit(wave_text, (10, 80))

        for i in range(facade.game_state['cowboy'].hp):
            screen.blit(facade.hp_texture, (10 + i * 45, 105))

        facade.game_state['cowboy'].draw(screen)
        for bullet in facade.game_state['cowboy'].bullets:
            bullet.draw(screen)
        facade.game_state['enemies'].draw(screen)
        facade.game_state['boosters'].draw(screen)
        for bullet in facade.game_state['eagle_bullets']:
            bullet.draw(screen)

        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((50, 50, 50))
        screen.blit(overlay, (0, 0))

        pause_text = self.title_font.render("Paused", True, (255, 255, 255))
        pause_rect = pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        screen.blit(pause_text, pause_rect)

        pygame.draw.rect(screen, (0, 255, 0), self.resume_button)
        pygame.draw.rect(screen, (0, 0, 0), self.resume_button, 2)
        resume_text = self.text_font.render("Resume", True, (0, 0, 0))
        resume_rect = resume_text.get_rect(center=self.resume_button.center)
        screen.blit(resume_text, resume_rect)


# Состояние окончания игры
class GameOverState(GameState):
    def __init__(self, facade):
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.restart_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 40, 200, 50)
        self.final_score = facade.game_state['score']

    def handle_events(self, facade):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if self.restart_button.collidepoint(mouse_pos):
                    facade.start_new_game()
                    facade.change_state(PlayingState())
        return True

    def update(self, facade):
        pass

    def draw(self, facade, screen):
        screen.fill((135, 206, 235))
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((50, 50, 50))
        screen.blit(overlay, (0, 0))

        game_over_text = self.title_font.render("Game Over", True, (255, 0, 0))
        game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        screen.blit(game_over_text, game_over_rect)

        score_display = self.text_font.render(f"Final Score: {self.final_score}", True, (255, 255, 255))
        score_rect = score_display.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(score_display, score_rect)

        pygame.draw.rect(screen, (0, 255, 0), self.restart_button)
        pygame.draw.rect(screen, (0, 0, 0), self.restart_button, 2)
        restart_text = self.text_font.render("Restart", True, (0, 0, 0))
        restart_rect = restart_text.get_rect(center=self.restart_button.center)
        screen.blit(restart_text, restart_rect)


# Абстрактный класс для команд
class Command(ABC):
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass


# Команда для движения
class MoveCommand(Command):
    def __init__(self, cowboy, dx, dy):
        self.cowboy = cowboy
        self.dx = dx
        self.dy = dy
        self.prev_x = cowboy.x
        self.prev_y = cowboy.y

    def execute(self):
        self.cowboy.x += self.dx * self.cowboy.speed * self.cowboy.speed_boost
        self.cowboy.y += self.dy * self.cowboy.speed * self.cowboy.speed_boost
        self.cowboy.x = max(0, min(self.cowboy.x, WIDTH - self.cowboy.rect.width))
        self.cowboy.y = max(0, min(self.cowboy.y, HEIGHT - self.cowboy.height))
        self.cowboy.update_rect()

    def undo(self):
        self.cowboy.x = self.prev_x
        self.cowboy.y = self.prev_y
        self.cowboy.update_rect()


# Команда для стрельбы
class ShootCommand(Command):
    def __init__(self, cowboy):
        self.cowboy = cowboy
        self.bullet = None

    def execute(self):
        if self.cowboy.shoot_timer <= 0:
            self.bullet = BulletFactory.create_bullet("player", self.cowboy.x + 16, self.cowboy.y)
            self.cowboy.bullets.append(self.bullet)
            self.cowboy.shoot_timer = (self.cowboy.shoot_cooldown // 2
                                       if self.cowboy.boost_active
                                       else self.cowboy.shoot_cooldown)
        self.cowboy.shoot_timer -= 1

    def undo(self):
        if self.bullet and self.bullet in self.cowboy.bullets:
            self.cowboy.bullets.remove(self.bullet)
            self.cowboy.shoot_timer = 0


# Абстрактный класс Prototype
class Prototype(ABC):
    @abstractmethod
    def clone(self):
        pass


# Абстрактный класс для объектов, которые можно обновлять и рисовать
class GameObject(ABC):
    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def draw(self, screen):
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
        self.prototype_linear = Bandit(0, 0, LinearMovementStrategy())
        self.prototype_zigzag = Bandit(0, 0, ZigZagMovementStrategy())

    def create_enemy(self, x):
        # 30% chance for ZigZagMovementStrategy, 70% for LinearMovementStrategy
        prototype = self.prototype_zigzag if random.random() < 0.3 else self.prototype_linear
        enemy = prototype.clone()
        enemy.x = x
        enemy.y = 0
        return enemy


class EagleFactory(EnemyFactory):
    def __init__(self):
        self.prototype = Eagle(0, 0, SinusoidalMovementStrategy())

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
class Entity(GameObject):
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

    def update(self):
        self.move()

    def draw(self, screen):
        pass


# Абстрактный класс для рендеринга (Bridge)
class EntityRenderer(ABC):
    @abstractmethod
    def render(self, screen, entity):
        pass


class CowboyRenderer(EntityRenderer):
    def render(self, screen, entity):
        screen.blit(entity.texture, (entity.x, entity.y))


# Класс игрока
class Cowboy(Entity, Subject):
    def __init__(self, x, y, renderer=CowboyRenderer()):
        Entity.__init__(self, x, y)
        Subject.__init__(self)
        self.renderer = renderer
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
        self.command_history = []

    def execute_command(self, command):
        command.execute()
        self.command_history.append(command)

    def undo_last_command(self):
        if self.command_history:
            last_command = self.command_history.pop()
            last_command.undo()

    def update_boost(self):
        if self.boost_active:
            self.boost_duration -= 1
            if self.boost_duration <= 0:
                self.shoot_cooldown = self.base_shoot_cooldown
                self.boost_active = False

    def set_health(self, new_health):
        old_health = self.hp
        self.hp = max(0, min(self.max_hp, new_health))
        if self.hp != old_health:
            self.notify("health_changed", {"health": self.hp})

    def apply_booster(self, duration, boost_value):
        if self.boost_active:
            self.boost_duration += duration
        else:
            self.boost_duration = duration
            self.shoot_cooldown = max(5, self.base_shoot_cooldown - boost_value)
            self.boost_active = True
        self.notify("booster_collected", {"duration": self.boost_duration})

    def draw(self, screen):
        self.renderer.render(screen, self)


# Декоратор для ускоренной стрельбы
class SpeedBoostDecorator:
    def __init__(self, cowboy):
        self.cowboy = cowboy

    def __call__(self):
        if self.cowboy.shoot_timer <= 0:
            bullet = BulletFactory.create_bullet("player", self.cowboy.x + 16, self.cowboy.y)
            self.cowboy.bullets.append(bullet)
            self.cowboy.shoot_timer = self.cowboy.shoot_cooldown // 2
        self.cowboy.shoot_timer -= 1


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


# Класс бандита с реализацией Prototype и Strategy
class Bandit(Entity, Prototype):
    def __init__(self, x, y, movement_strategy=LinearMovementStrategy()):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['bandit']
        self.hp = 2
        self.base_speed = 1
        self.max_speed = 3
        self.movement_strategy = movement_strategy
        self.angle = 0  # Added for ZigZagMovementStrategy

    def clone(self):
        return Bandit(self.x, self.y, self.movement_strategy)

    def move(self):
        self.movement_strategy.move(self, time=None)

    def update(self, time=None):
        self.move()
        self.update_rect()

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))


# Класс орла с реализацией Prototype и Strategy
class Eagle(Entity, Prototype):
    def __init__(self, x, y, movement_strategy=SinusoidalMovementStrategy()):
        super().__init__(x, y)
        self.texture = ResourceManager().textures['eagle']
        self.hp = 1
        self.angle = 0
        self.shoot_timer = random.randint(30, 60)
        self.base_speed = 1
        self.max_speed = 3
        self.movement_strategy = movement_strategy

    def clone(self):
        return Eagle(self.x, self.y, self.movement_strategy)

    def move(self):
        self.movement_strategy.move(self, time=None)

    def update(self, time=None):
        self.move()
        self.shoot_timer -= 1

    def shoot(self):
        if self.shoot_timer <= 0:
            self.shoot_timer = random.randint(30, 60)
            return BulletFactory.create_bullet("eagle", self.x + 16, self.y + 32)
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
        cowboy.apply_booster(self.duration, self.boost_value)

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
            cowboy.set_health(cowboy.hp + self.heal_value)

    def draw(self, screen):
        screen.blit(self.texture, (self.x, self.y))


# Композит для управления группами объектов
class CompositeGroup(GameObject):
    def __init__(self):
        self.children = []

    def add(self, obj):
        self.children.append(obj)

    def remove(self, obj):
        self.children.remove(obj)

    def update(self):
        for obj in self.children[:]:
            obj.update()

    def draw(self, screen):
        for obj in self.children:
            obj.draw(screen)


# Адаптер для WASD ввода
class WASDInput:
    def read_input(self):
        keys = pygame.key.get_pressed()
        return {
            'up': keys[pygame.K_w],
            'down': keys[pygame.K_s],
            'left': keys[pygame.K_a],
            'right': keys[pygame.K_d]
        }


class InputAdapter:
    def __init__(self, adaptee):
        self.adaptee = adaptee

    def get_controls(self):
        raw = self.adaptee.read_input()
        return {
            'move_x': -1 if raw['left'] else (1 if raw['right'] else 0),
            'move_y': -1 if raw['up'] else (1 if raw['down'] else 0)
        }


# Builder и Director для создания игрового состояния
class GameStateBuilder:
    def __init__(self):
        self.game_state = {}

    def set_cowboy(self):
        self.game_state['cowboy'] = Cowboy(WIDTH // 2, HEIGHT - 64)
        return self

    def set_enemies(self):
        self.game_state['enemies'] = CompositeGroup()
        wave1 = CompositeGroup()
        wave2 = CompositeGroup()
        wave3 = CompositeGroup()
        self.game_state['enemies'].add(wave1)
        self.game_state['enemies'].add(wave2)
        self.game_state['enemies'].add(wave3)
        self.game_state['waves'] = [wave1, wave2, wave3]
        return self

    def set_boosters(self):
        self.game_state['boosters'] = CompositeGroup()
        return self

    def set_eagle_bullets(self):
        self.game_state['eagle_bullets'] = []
        return self

    def set_timers(self):
        self.game_state['spawn_timer'] = 0
        self.game_state['score'] = 0
        self.game_state['time'] = 0
        self.game_state['wave_phase'] = 0
        self.game_state['current_wave'] = 0
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
                .build())


# Фасад для упрощения работы с игровым движком
class GameEngineFacade(Subject):
    def __init__(self):
        super().__init__()
        self.resource_manager = ResourceManager.get_instance()
        self.builder = GameStateBuilder()
        self.director = GameDirector(self.builder)
        self.bandit_factory = BanditFactory()
        self.eagle_factory = EagleFactory()
        self.speed_booster_factory = SpeedBoosterFactory()
        self.heal_factory = HealFactory()
        self.wasd_input = InputAdapter(WASDInput())
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.hp_texture = pygame.transform.scale(self.resource_manager.textures['hp'], (40, 20))
        self.notifications = []
        self.game_state = None
        self.current_state = MenuState()

    def add_notification(self, text, x, y, duration, color):
        notification = Notification(text, x, y, duration, color)
        self.notifications.append(notification)

    def start_new_game(self):
        self.game_state = self.director.construct_game_state()
        self.notifications = []
        score_observer = ScoreObserver(self.game_state)
        ui_observer = UIObserver(self)
        game_state_observer = GameStateObserver(self)
        self.attach(score_observer)
        self.attach(ui_observer)
        self.game_state['cowboy'].attach(ui_observer)
        self.game_state['cowboy'].attach(game_state_observer)

    def change_state(self, new_state):
        self.current_state = new_state

    def handle_events(self):
        return self.current_state.handle_events(self)

    def update(self):
        self.current_state.update(self)

    def draw(self, screen):
        self.current_state.draw(self, screen)


# Основной игровой цикл
def main():
    engine = GameEngineFacade()
    running = True
    while running:
        running = engine.handle_events()
        engine.update()
        engine.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()