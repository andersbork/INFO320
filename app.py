from flask import Flask, request, render_template, url_for
from SPARQLWrapper import SPARQLWrapper, JSON
import requests

app = Flask(__name__)

SPARQL_ENDPOINT = "http://localhost:8080/sparql"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    search = request.form.get('search')
    genres = request.form.getlist('genres')
    rating = request.form.get('rating')
    min_year = request.form.get('min_year')
    max_year = request.form.get('max_year')
    sort_by = request.form.get('sort_by')
    sort_order = request.form.get('sort_order', 'desc')

    #base query
    query = """
    PREFIX : <http://example.org/ontology#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?movie ?title ?rd ?rating ?duration
        (GROUP_CONCAT(DISTINCT ?genreName; SEPARATOR=", ") AS ?genres) 
        (GROUP_CONCAT(DISTINCT ?actorName; SEPARATOR=", ") AS ?actorNames) 
        (GROUP_CONCAT(DISTINCT STR(?actor); SEPARATOR=", ") AS ?actorIDs)
        (Group_CONCAT(DISTINCT STR(?studio); SEPARATOR=", ") AS ?studioIDs)
        (GROUP_CONCAT(DISTINCT ?studioName; SEPARATOR=", ") AS ?studioNames)
    WHERE {
        ?movie a :Movie ;
               :title ?title ;
               :releaseDate ?rd ;
               :rating ?rating ;
               :duration ?duration .
        
        ?movie :actedInBy ?actor.
        ?actor foaf:name ?actorName.
        ?movie :hasGenre ?genre .
        ?genre :name ?genreName .
        ?movie :madeByStudio ?studio.
        ?studio :name ?studioName.
    
    """

    #filters
    filters = []
    if search:
        filters.append(f'(regex(LCASE(?title), LCASE("{search}")) || regex(LCASE(?actorName), LCASE("{search}")))')
    if genres:
        for genre in genres:
            query += f"""
            ?movie :hasGenre ?g_{genre} .
            ?g_{genre} :name "{genre}" .
            """

    if rating:
        filters.append(f'?rating >= {rating}')
    if min_year:
        filters.append(f'?rd >= "{min_year}-01-01"^^xsd:date')
    if max_year:
        filters.append(f'?rd <= "{max_year}-12-31"^^xsd:date')
    if filters:
        query += " FILTER(" + " && ".join(filters) + ") "
    
    query += " } GROUP BY ?movie ?title ?rd ?duration ?rating "
    
    if sort_by:
        query += f" ORDER BY {'DESC' if sort_order == 'desc' else 'ASC'}(?{sort_by})"

    print(f"SPARQL Query: {query}")  #debugging

    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"Query Results: {results}")  #debugging
        return render_template('results.html', results=results['results']['bindings'], sort_by=sort_by, sort_order=sort_order, zip=zip)
    except Exception as e:
        print(f"An error occurred: {str(e)}")  # debugging
        return f"An error occurred: {str(e)}"

@app.route('/actor_info')
def actor_info():
    actor = request.args.get('id')
    actor_id = actor.split('/')[-1]
    query = f"""
    PREFIX : <http://example.org/ontology#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?name ?gender 
        (GROUP_CONCAT(DISTINCT CONCAT(?movieTitle, " (", STR(?movie), "):", ?charName); SEPARATOR="||") AS ?moviesWithCharacters)
    WHERE {{
        ?id a :Actor;
            foaf:name ?name;
            :gender ?gender;
            :actsIn ?movie ;
            :plays ?char .
        ?char :inMovie ?movie.
        ?movie :title ?movieTitle.
        ?char foaf:name ?charName.
        FILTER(?id = <{actor}>)
    }}
    GROUP BY ?name ?gender
    """
    print(f"SPARQL Query: {query}")  #debugging

    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"Actor Query Results: {results}")  #debugging
        return render_template('actor_info.html', actor=results['results']['bindings'][0])
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"

@app.route('/movie_info')
def movie_info():
    movie_id = request.args.get('id')
    query = f"""
    PREFIX : <http://example.org/ontology#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT  ?title ?releaseDate ?duration ?rating 
        (GROUP_CONCAT(DISTINCT ?genreName; SEPARATOR=", ") AS ?genres)
        (GROUP_CONCAT(DISTINCT ?keywordName; SEPARATOR=", ") AS ?keywords)
        (GROUP_CONCAT(DISTINCT CONCAT(?studioName, "::", STR(?studio)); SEPARATOR="||") AS ?studios)
        (GROUP_CONCAT(DISTINCT CONCAT(?actorName, "::", STR(?actor)); SEPARATOR="||") AS ?cast)
        (GROUP_CONCAT(DISTINCT CONCAT(?directorName, "::", STR(?d)); SEPARATOR="||") AS ?directors)
        (GROUP_CONCAT(DISTINCT CONCAT(?producerName, "::", STR(?p)); SEPARATOR="||") AS ?producers)
        (GROUP_CONCAT(DISTINCT CONCAT(?screenplayName, "::", STR(?s)); SEPARATOR="||") AS ?screenplays)
        (GROUP_CONCAT(DISTINCT CONCAT(?editorName, "::", STR(?e)); SEPARATOR="||") AS ?editors)
        (GROUP_CONCAT(DISTINCT CONCAT(?writerName, "::", STR(?w)); SEPARATOR="||") AS ?writers)
    WHERE {{
        ?movie a :Movie ;
               :title ?title ;
               :releaseDate ?releaseDate ;
               :rating ?rating ;
               :duration ?duration ;
               :actedInBy ?actor ;
               :hasGenre ?genre;
               :madeByStudio ?studio;
               :hasKeyword ?k.
        ?studio :name ?studioName.
        ?k :name ?keywordName.
        OPTIONAL {{ ?actor foaf:name ?actorName. }}
        OPTIONAL {{ ?genre :name ?genreName. }}

        OPTIONAL {{ ?movie :hasDirector ?d. ?d foaf:name ?directorName. }}
        OPTIONAL {{ ?movie :hasProducer ?p. ?p foaf:name ?producerName. }}
        OPTIONAL {{ ?movie :hasScreenplay ?s. ?s foaf:name ?screenplayName. }}
        OPTIONAL {{ ?movie :hasEditor ?e. ?e foaf:name ?editorName. }}
        OPTIONAL {{ ?movie :hasWriter ?w. ?w foaf:name ?writerName. }}
        OPTIONAL {{ ?movie :madeByStudio ?studio. ?studio :name ?studioName.}}


        FILTER(?movie = <{movie_id}>)
    }}
    GROUP BY ?title ?releaseDate ?duration ?rating
    """
    print(f"SPARQL Query: {query}")  #debugging

    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"Movie Query Results: {results}")  # debugging
        return render_template('movie_info.html', movie=results['results']['bindings'][0], zip=zip)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"
    
@app.route('/crew_info')
def crew_info():
    crew_id = request.args.get('id')
    query = f"""
    PREFIX : <http://example.org/ontology#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?name
        (GROUP_CONCAT( CONCAT(?movieTitle, " (", STR(?movie), ")-", ?roleLabel); SEPARATOR="||") AS ?moviesWithRoles)
    WHERE {{
        ?crew a :Crew ;
              foaf:name ?name ;
              :workedOn ?movie .
        ?movie :title ?movieTitle .

        OPTIONAL {{ ?movie :hasDirector ?crew. BIND("Director" AS ?roleLabel) }}
        OPTIONAL {{ ?movie :hasProducer ?crew. BIND("Producer" AS ?roleLabel) }}
        OPTIONAL {{ ?movie :hasScreenplay ?crew. BIND("Screenplay" AS ?roleLabel) }}
        OPTIONAL {{ ?movie :hasEditor ?crew. BIND("Editor" AS ?roleLabel) }}
        OPTIONAL {{ ?movie :hasWriter ?crew. BIND("Writer" AS ?roleLabel) }}

        FILTER(?crew = <{crew_id}>)
    }}
    GROUP BY ?name
    """
    print(f"SPARQL Query: {query}")  #debugging

    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"Crew Query Results: {results}")  #debugging
        if results['results']['bindings']:
            return render_template('crew_info.html', crew=results['results']['bindings'][0])
        else:
            return "No results found for the given crew member ID."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"
@app.route('/studio_info')
def studio_info():
    studio_id = request.args.get('id')
    query = f"""
    PREFIX : <http://example.org/ontology#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?name 
        (GROUP_CONCAT(DISTINCT CONCAT(?movieTitle, " (", STR(?movie), ")"); SEPARATOR="||") AS ?moviesWithID)
    WHERE {{
        ?studio a :Studio ;
              :name ?name.
        ?movie :title ?movieTitle .
        ?movie :madeByStudio ?studio.
        FILTER(?studio = <{studio_id}>)
    }}
    GROUP BY ?name
    """
    print(f"SPARQL Query: {query}")  # debugging

    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"Studio Query Results: {results}")  #debugging
        if results['results']['bindings']:
            return render_template('studio_info.html', studio=results['results']['bindings'][0], zip=zip)
        else:
            return "No results found for the given studio ID."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"
    return f"Displaying information for studio ID: {studio_id}"
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
