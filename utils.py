
def convert_to_set(dict_movies):
    return {(movie['id'], movie['poster_path'], movie['title'], movie['year']) for movie in dict_movies}

def joint_films(actors_list):
    all_films = [convert_to_set(actor['movies']) for actor in actors_list]
    common_movies = set.intersection(*all_films)
    return [
        {'id': film[0], 'poster': f"https://image.tmdb.org/t/p/w300{film[1]}", 'title': film[2], 'year': film[3]}
        for film in common_movies
    ]
