java -version
cd /d "[YOUR_PATH]\ontop-cli-5.1.1"

.\ontop.bat endpoint --ontology=input/movieOntology.rdf --mapping=input/movieOntology.obda --properties=input/movieOntology.properties --cors-allowed-origins=http://yasgui.org
