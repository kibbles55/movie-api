import httpx
import os
from dotenv import load_dotenv
import redis.asyncio as redis
import json
from redis.exceptions import RedisError, ConnectionError

load_dotenv()  # читає .env
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
REDIS_URL = os.getenv('REDIS_URL')

class TMDbClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str, redis_url=REDIS_URL):
        self.api_key = api_key
        self.redis_url = redis_url
        self.redis = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def get(self, endpoint: str, params: dict = None, cache_ttl: int = 86400):
        if params is None:
            params = {}

        cache_key = f"tmdb:{endpoint}:{json.dumps(params, sort_keys=True)}"
        cached = None

        # Спроба взяти з кешу, без падіння при недоступності Redis
        try:
            cached = await self.redis.get(cache_key)
        except ConnectionError:
            print("Redis недоступний, працюємо без кешу")

        if cached:
            print("з кешу")
            return json.loads(cached)

        # Запит до TMDb
        async with httpx.AsyncClient() as client:
            params["api_key"] = self.api_key
            url = f"{self.BASE_URL}/{endpoint}"
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        # Спроба записати в кеш
        try:
            await self.redis.set(cache_key, json.dumps(data), ex=cache_ttl)
        except ConnectionError:
            print("Redis недоступний, кеш не збережено")

        return data

    async def search_person(self, name: str):
        return await self.get("search/person", params={"query": name, "language": "uk"})

    async def search_movie(self, title: str):
        return await self.get("search/movie", params={"query": title, "language": "uk"})

    async def movie_details(self, movie_id: int, append: str = "credits,videos,similar"):
        return await self.get(f"movie/{movie_id}", params={"language": "uk", "append_to_response": append})

    async def actor_credits(self, actor_id: int):
        return await self.get(f"person/{actor_id}/movie_credits", params={"language": "uk"})

    async def popular_movies(self):
        popular_movies = await self.get(f"movie/popular", params={"language": "uk"})
        return [
            {
                "id": movie["id"],
                "title": movie["title"],
                "overview": movie["overview"],
                "poster_path": movie["poster_path"],
                "release_date": movie["release_date"],
                "vote_average": movie["vote_average"],
            }
            for movie in popular_movies.get("results", [])
        ]

tmdb = TMDbClient(api_key=TMDB_API_KEY)

class Actor:
    def __init__(self, name):
        self.name = name
        self.actor_id = None
        self.actor_info = {}
        self.actor_films = []

    async def actor_info_method(self):
        search_result = await tmdb.search_person(self.name)
        if not search_result:
            return False

        actor = search_result['results'][0]
        self.actor_id = actor['id']
        self.actor_films = await self.load_movies()
        self.actor_info = {
            'id': self.actor_id,
            'name': actor['name'],
            'photo': f"https://image.tmdb.org/t/p/w500{actor['profile_path']}" if actor['profile_path'] else None,
            'movies': self.actor_films
        }
        return self.actor_info

    async def load_movies(self):
        movie_credits = await tmdb.actor_credits(self.actor_id)
        films = []
        if movie_credits['cast']:
            for film in movie_credits['cast']:
                films.append({
                    'id': film['id'],
                    'poster_path': film['poster_path'] if film['poster_path'] else None,
                    'title': film['title'],
                    'year': film['release_date'][0:4] if film['release_date'] else "N/A"
                })
        else:
            print("Фільмографію не знайдено.")

        return films

class Movie:
    def __init__(self, title):
        self.title = title
        self.movie_id = None
        self.movie_details = {}

    async def movie_info(self):
        search_result = await tmdb.search_movie(self.title)

        if not search_result.get("results"):
            return {
                "success": False,
                "message": f"Фільм '{self.title}' не знайдено",
            }

        # Беремо перший результат
        movie = search_result["results"][0]
        self.movie_id = movie["id"]

        # Отримуємо деталі з credits + similar (append_to_response)
        movie_details = await tmdb.movie_details(self.movie_id)

        cast = [actor["name"] for actor in movie_details.get("credits", {}).get("cast", [])]
        genres = [g["name"] for g in movie_details.get("genres", [])]
        similar = [s["title"] for s in movie_details.get("similar", {}).get("results", [])]

        self.movie_details = {
            "success": True,
            "id": self.movie_id,
            "title": movie_details.get("title"),
            "cast": cast,
            "poster": f"https://image.tmdb.org/t/p/w300{movie_details.get('poster_path')}"
                      if movie_details.get("poster_path") else None,
            "backdrop": f"https://image.tmdb.org/t/p/w500{movie_details.get('backdrop_path')}"
                        if movie_details.get("backdrop_path") else None,
            "genres": genres,
            "release_date": movie_details.get("release_date"),
            "overview": movie_details.get("overview"),
            "vote_count": movie_details.get("vote_count"),
            "similar": similar,
        }

        return self.movie_details


