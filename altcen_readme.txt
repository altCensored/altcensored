# python venv has been used, needs to be readded, creating dir venv in this dir.

# start on ubuntu server with

cd /your/dir/alt2 # change to this dir
. venv/bin/activate
export FLASK_APP=alt2
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=80