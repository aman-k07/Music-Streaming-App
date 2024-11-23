####### import neccesarry modules #####
from app import *
from flask_restful import Api, reqparse, Resource, fields, marshal_with
import json
from flask import make_response
from werkzeug.exceptions import HTTPException


# Initialize Flask-RESTful with the app
api = Api(app)


# Validations
class BaseHTTPError(HTTPException):
    def __init__(self, status_code, message):
        self.response = make_response(message, status_code)

class NotFoundError(BaseHTTPError):
    def __init__(self, message):
        super().__init__(404, message)

class UnauthorizedError(BaseHTTPError):
    def __init__(self, message):
        super().__init__(409, message)
        
class ConflictError(BaseHTTPError):
    def __init__(self, message):
        super().__init__(415, message)


class BusinessValidationError(HTTPException):
    def __init__(self, status_code, error_code, error_message):
        message = {"error_code": error_code, "error_message": error_message}
        self.response = make_response(json.dumps(message), status_code)
        
       
# Output Fields in JSON Format

songs_fields = {"id": fields.Integer, "title": fields.String, "singer": fields.String, "date": fields.String,
                "lyrics": fields.String, "genre": fields.String, "filename":fields.String,
                "user_id": fields.Integer
}

upload_song_parser = reqparse.RequestParser()
upload_song_parser.add_argument("title")
upload_song_parser.add_argument("singer")
upload_song_parser.add_argument("date")
upload_song_parser.add_argument("lyrics")
upload_song_parser.add_argument("genre")
upload_song_parser.add_argument("filename")
upload_song_parser.add_argument("user_id")

edit_song_parser = reqparse.RequestParser()
edit_song_parser.add_argument("title")
edit_song_parser.add_argument("singer")
edit_song_parser.add_argument("date")
edit_song_parser.add_argument("lyrics")
edit_song_parser.add_argument("genre")
edit_song_parser.add_argument("filename")


# API Classes
class SongAPI(Resource):
    @marshal_with(songs_fields)
    def get(self, song_id):
        song = Songs.query.get(song_id)
        if song:
            return song, 200
        else:
            raise NotFoundError(message="Song not found")
        
        
    def delete(self, uploader, song_id):
        # check if song exists
        song = Songs.query.get(song_id)

        if song is None:
            raise NotFoundError(message="Song not found")
        
        # check if user_id is the uploader
        if uploader != song.user_id:
            raise UnauthorizedError(message="User not authorized to delete this song")
        
        Songs_in_Album.query.filter_by(song_id=song_id).delete()  # 1st delter it from Album
        Songs_in_Playlist.query.filter_by(song_id=song_id).delete()  # then delete it from Playlist
        Rating.query.filter_by(song_id=song_id).delete()  # then delete all its reatings

        db.session.delete(song)  # finally delete the song from the database
        db.session.commit()
        return "Successfully Deleted", 200
    
    
    @marshal_with(songs_fields)
    def post(self):
        # Get the data from request body
        args = upload_song_parser.parse_args()
        title = args.get("title", None)
        singer = args.get("singer", None)
        date = args.get("date", None)
        lyrics = args.get("lyrics", None)
        genre =args.get("genre", None)
        filename = args.get("filename", None)
        user_id = args.get("user_id", None)
        
        # check if a song with same title & singer already exits
        existing_song = Songs.query.filter_by(title=title, singer=singer).first() 
        if existing_song:
            raise ConflictError(message="Song already exist")
        
        # check if user is a creator
        user = Users.query.get(user_id)
        if not (user.creator==True):
            raise UnauthorizedError(message="User is not authorized to upload songs")
        
        if (title is None):
            raise BusinessValidationError(status_code=400, error_code="SONG001", 
                                          error_message="Song Title is required.")
        
        
        if (singer is None):
            raise BusinessValidationError(status_code=400,error_code="SONG002",
                                          error_message="Song Artists is required.")
        
        if (date is None):
            raise BusinessValidationError(status_code=400,error_code="SONG003",
                                          error_message="Song Release Date is required.")
            
        if (lyrics is None):
            raise BusinessValidationError(status_code=400,error_code="SONG004",
                                          error_message="Song Lyrics is required.")
            
        if (genre is None):
            raise BusinessValidationError(status_code=400,error_code="SONG005",
                                          error_message="Song Genres is required.")
        
        if (filename is None):
            raise BusinessValidationError(status_code=400,error_code="SONG006",
                                          error_message="Song File is required.")
                  
        song = Songs(title=title,singer=singer,date=date,lyrics=lyrics,genre=genre,
                     filename=filename,user_id=user_id)  
        
        db.session.add(song)
        db.session.commit()

        return song, 201
    
    
    @marshal_with(songs_fields)
    def put(self, uploader, song_id): 
        song = Songs.query.get(song_id)

        if song is None:
            raise NotFoundError(message="Song not found")
        
        # check if user is uploader of song
        if uploader!=song.user_id:
            raise UnauthorizedError(message="User is not authorized to update these song")

        # Get the data from request body
        args = edit_song_parser.parse_args()
        song.title = args.get("title", None)
        song.singer = args.get("singer", None)
        song.date = args.get("date", None)
        song.lyrics = args.get("lyrics", None)
        song.genre =args.get("genre", None)
        song.filename = args.get("filename", None)

        if (song.title is None):
            raise BusinessValidationError(status_code=400,error_code="SONG001",
                                          error_message="Song Title is required.")
        
        
        if (song.singer is None):
            raise BusinessValidationError(status_code=400,error_code="SONG002",
                                          error_message="Song Artists is required.")
        
        if (song.date is None):
            raise BusinessValidationError(status_code=400,error_code="SONG003",
                                          error_message="Song Release Date is required.")
            
        if (song.lyrics is None):
            raise BusinessValidationError(status_code=400,error_code="SONG004",
                                          error_message="Song Lyrics is required.")
            
        if (song.genre is None):
            raise BusinessValidationError(status_code=400,error_code="SONG005",
                                          error_message="Song Genres is required.")
        
        if (song.filename is None):
            raise BusinessValidationError(status_code=400,error_code="SONG006",
                                          error_message="Song File is required.")

        db.session.commit()
        return song,201
    
    
api.add_resource(SongAPI, '/api/user/creator/<int:uploader>/song/<int:song_id>', '/api/user/song/<int:song_id>',
                 '/api/user/creator/song')


# GET : /api/user/song/<int:song_id>
# DELETE, PUT : /api/user/creator/<int:uploader>/song/<int:song_id>
# POST : api/user/creator/song


# checks if this file is the main program being run
if __name__ == '__main__' :
     app.run(debug=False,port=1999)