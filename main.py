from utils import *
from fastapi import FastAPI
import asyncio
from models import Actor, Movie, tmdb
app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "API працює 🚀"}


@app.get("/movies/{title}")
async def get_movie(title: str):
    movie = Movie(title)
    movie_info = await movie.movie_info()
    return movie_info

@app.get("/movies_popular")
async def get_popular_movies():
    popular_movies = await tmdb.popular_movies()
    return popular_movies

@app.get("/actor/{name}")
async def actor(name: str):
    actor_data = await Actor(name).actor_info_method()

    if not actor_data:
        return {
            "success": False,
            "message": f"Актор '{name}' не знайдений",
            "actor": None
        }

    return {
        "success": True,
        "message": f"Актор '{actor_data['name']}' знайдений",
        "actor": actor_data
    }

@app.get("/movies/common/{actors}")
async def common_movies(actors: str):
    names = actors.split(",")
    tasks = [Actor(name).actor_info_method() for name in names]
    actors_list = await asyncio.gather(*tasks)

    if not actors_list:
        return {
            "success": False,
            "message": "Актори не знайдені або спільних фільмів немає",
            "actors": names,
            "count": 0,
            "movies": []
        }

    movies = joint_films(actors_list)

    if not movies:
        return {
            "success": False,
            "message": "Спільних фільмів не знайдено",
            "actors": names,
            "count": 0,
            "movies": []
        }

    return {
        "success": True,
        "message": f"Знайдено {len(movies)} спільних фільмів",
        "actors": names,
        "count": len(movies),
        "movies": movies
    }
