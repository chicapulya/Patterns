import arcade
import random
from abc import ABC, abstractmethod
from copy import deepcopy

# Константы
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 5
BULLET_SPEED = 10


# Singleton для управления ресурсами
class ResourceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.textures = {
                'cowboy': arcade.load_texture("assets/Cowboy4_idle with gun_0.png"),
                'bandit': arcade.load_texture("assets/pixel_skeleton_uno.png"),
                'eagle': arcade.load_texture("assets/spr_enemy_boss_09_dead.png")
            }
            cls.sounds = {
                'shot': arcade.load_sound("shot.wav")
            }
        return cls._instance


# Абстрактная фабрика врагов
class EnemyFactory(ABC):
    @abstractmethod
    def create_enemy(self):
        pass


class BanditFactory(EnemyFactory):
    def create_enemy(self):
        return Bandit()


class EagleFactory(EnemyFactory):
    def create_enemy(self):
        return Eagle()


# Prototype для клонирования врагов
class EnemyPrototype:
    def __init__(self):
        self.prototype = None

    def clone(self):
        return deepcopy(self.prototype)


# Builder для бустеров
class BoosterBuilder:
    def __init__(self):
        self.booster = Booster()

    def set_speed(self, value):
        self.booster.speed_boost = value
        return self

    def set_damage(self, value):
        self.booster.damage_boost = value
        return self

    def build(self):
        return self.booster


# Классы игры
class Player(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = ResourceManager().textures['cowboy']
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = 100
        self.speed = PLAYER_SPEED
        self.damage = 1

    def update(self):
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Ограничение движения
        self.center_x = max(self.width / 2, min(SCREEN_WIDTH - self.width / 2, self.center_x))
        self.center_y = max(self.height / 2, min(SCREEN_HEIGHT - self.height / 2, self.center_y))


class Bullet(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(5, (255, 255, 0), True)
        self.center_x = x
        self.center_y = y
        self.change_y = BULLET_SPEED

    def update(self):
        self.center_y += self.change_y
        if self.center_y > SCREEN_HEIGHT:
            self.kill()


class Bandit(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = ResourceManager().textures['bandit']
        self.center_x = random.randint(0, SCREEN_WIDTH)
        self.center_y = SCREEN_HEIGHT - 50
        self.health = 2

    def update(self):
        self.center_y -= 1
        if self.center_y < 0:
            self.kill()


class Eagle(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = ResourceManager().textures['eagle']
        self.center_x = random.randint(0, SCREEN_WIDTH)
        self.center_y = SCREEN_HEIGHT
        self.health = 1

    def update(self):
        self.center_y -= 2
        self.center_x += random.randint(-1, 1)
        if self.center_y < 0:
            self.kill()


class Booster(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = arcade.make_soft_circle_texture(20, (0, 255, 0))
        self.center_x = random.randint(0, SCREEN_WIDTH)
        self.center_y = SCREEN_HEIGHT
        self.speed_boost = 0
        self.damage_boost = 0

    def update(self):
        self.center_y -= 2
        if self.center_y < 0:
            self.kill()


class CowboyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Cowboy Game")

        # Инициализация фабрик и прототипов
        self.bandit_factory = BanditFactory()
        self.eagle_factory = EagleFactory()
        self.bandit_prototype = EnemyPrototype()
        self.bandit_prototype.prototype = Bandit()

        # Списки объектов
        self.player = Player()
        self.bullet_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.booster_list = arcade.SpriteList()

        self.score = 0
        self.spawn_timer = 0

    def setup(self):
        arcade.set_background_color(arcade.color.SKY_BLUE)

    def on_draw(self):
        arcade.start_render()
        self.player.draw()
        self.bullet_list.draw()
        self.enemy_list.draw()
        self.booster_list.draw()
        arcade.draw_text(f"Score: {self.score}", 10, 20, arcade.color.WHITE, 14)

    def on_update(self, delta_time):
        self.player.update()
        self.bullet_list.update()
        self.enemy_list.update()
        self.booster_list.update()

        # Проверка столкновений
        for bullet in self.bullet_list:
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)
            for enemy in hit_list:
                enemy.health -= self.player.damage
                if enemy.health <= 0:
                    enemy.kill()
                    self.score += 1
                bullet.kill()

        # Сбор бустеров
        boosters_hit = arcade.check_for_collision_with_list(self.player, self.booster_list)
        for booster in boosters_hit:
            self.player.speed += booster.speed_boost
            self.player.damage += booster.damage_boost
            booster.kill()

        # Спавн врагов и бустеров
        self.spawn_timer += delta_time
        if self.spawn_timer > 1.0:
            self.spawn_timer = 0
            if random.random() < 0.6:
                self.enemy_list.append(self.bandit_factory.create_enemy())
            else:
                self.enemy_list.append(self.eagle_factory.create_enemy())

            if random.random() < 0.2:
                builder = BoosterBuilder()
                booster = builder.set_speed(2).set_damage(1).build()
                self.booster_list.append(booster)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.LEFT:
            self.player.change_x = -self.player.speed
        elif key == arcade.key.RIGHT:
            self.player.change_x = self.player.speed
        elif key == arcade.key.UP:
            self.player.change_y = self.player.speed
        elif key == arcade.key.DOWN:
            self.player.change_y = -self.player.speed
        elif key == arcade.key.SPACE:
            bullet = Bullet(self.player.center_x, self.player.center_y + 20)
            self.bullet_list.append(bullet)
            arcade.play_sound(ResourceManager().sounds['shot'])

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.RIGHT):
            self.player.change_x = 0
        elif key in (arcade.key.UP, arcade.key.DOWN):
            self.player.change_y = 0


def main():
    game = CowboyGame()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()