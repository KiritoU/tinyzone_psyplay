import logging
from time import sleep

from slugify import slugify

from _db import database
from helper import helper
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class PsyPlay:
    def __init__(self, film: dict, episodes: dict):
        self.film = film
        self.film["quality"] = self.film["extra_info"].get("quality", "HD")
        self.episodes = episodes
        self.film["fondo_player"] = film.get("cover_src", "")
        self.film["poster_url"] = film.get("cover_src", "")
        self.episode = {}

    def insert_movie_details(self, post_id):
        if not self.episodes:
            return

        logging.info("Inserting movie players")

        movie_links = [
            f"https://www.2embed.to/embed/tmdb/movie?id={self.episodes.get('tmdb_id', '0')}"
        ]
        players = helper.get_players_iframes(movie_links)
        postmeta_data = [
            (post_id, "player", str(len(players))),
            (post_id, "_player", "field_5640ccb223222"),
        ]
        postmeta_data.extend(
            helper.generate_players_postmeta_data(
                post_id, players, self.film["quality"]
            )
        )

        helper.insert_postmeta(postmeta_data)

    def insert_root_film(self) -> list:
        condition_post_name = slugify(self.film["post_title"])
        condition = f"""post_name = '{condition_post_name}' AND post_type='{self.film["post_type"]}'"""
        be_post = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
        )
        if not be_post:
            logging.info(f'Inserting root film: {self.film["post_title"]}')
            post_data = helper.generate_film_data(
                self.film["post_title"],
                self.film["description"],
                self.film["post_type"],
                self.film["trailer_id"],
                self.film["cover_src"],
                self.film["extra_info"],
            )

            return [helper.insert_film(post_data), True]
        else:
            return [be_post[0][0], False]

    def insert_episode(self, post_id):
        for episode_number, episode_title in self.episode.items():
            if not episode_title:
                episode_title = f"Episode {episode_number}"
            episode_title = (
                self.film["post_title"]
                + f' - Season {self.film["season_number"]}: '
                + episode_title
                + f" - Episode {episode_number}"
            )

            condition_episode_name = slugify(episode_title)
            condition = f'post_name = "{condition_episode_name}"'
            be_post = database.select_all_from(
                table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
            )
            if be_post:
                continue

            logging.info(f"Inserting episode: {episode_title}")

            episode_data = helper.generate_episode_data(
                post_id,
                episode_title,
                self.film["season_number"],
                episode_number,
                self.film["post_title"],
                self.film["fondo_player"],
                self.film["poster_url"],
                self.film["quality"],
                [
                    f"https://www.2embed.to/embed/tmdb/tv?id={self.episodes.get('tmdb_id', '0')}&s={self.film['season_number']}&e={episode_number}"
                ],
            )

            helper.insert_episode(episode_data)

    def insert_film(self):
        self.film["post_title"] = self.film["title"]

        post_id, isNewPostInserted = self.insert_root_film()
        if not post_id:
            return

        if self.film["post_type"] != CONFIG.TYPE_TV_SHOWS:
            if isNewPostInserted:
                self.insert_movie_details(post_id)
            return

        for key, value in self.episodes.items():
            if "season" in key.lower():
                self.film["season_number"] = helper.get_season_number(key)
                self.episode = value
                self.insert_episode(post_id)

        sleep(1)
