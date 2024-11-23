####### import neccesarry modules #####
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import matplotlib.pyplot as plt


# Create a Flask application instance
app = Flask(__name__)

# Set the directory for uploaded audio files
app.config['UPLOAD_FOLDER'] = 'static/audio'

# Configure the SQLAlchemy database URI to use a SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///muzic_db.sqlite3"

# Set a secret key for the application to keep client-side sessions secure
app.secret_key = 'ELfkVqmHSQT854$'

# Initialize SQLAlchemy with the app
db = SQLAlchemy(app)

# Set up Flask-Login and initialize it with the app
login_manager = LoginManager()
login_manager.init_app(app)

# Set the endpoint for the login page
login_manager.login_view = 'user_login'

# Push an application context manually to make certain variables globally accessible
app.app_context().push()


################################################### Models ###############################################

class Users(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    creator = db.Column(db.Boolean, default=False)
    blacklisted = db.Column(db.Boolean, default=False)
    songs = db.relationship('Songs', backref='uploader', lazy=True)
    playlists = db.relationship('Playlist', backref='user', lazy=True)
    albums = db.relationship('Album', backref='user', lazy=True)
    ratings = db.relationship('Rating', backref='user', lazy=True)
    

class Songs(db.Model):
    __tablename__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    singer = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    lyrics = db.Column(db.String, nullable=False)
    genre = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    __table_args__ = (UniqueConstraint('title', 'singer', name='unique_singer_title'),)
  
    
class Playlist(db.Model):
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    songs_in_playlist = db.relationship('Songs_in_Playlist', backref='playlist', lazy=True)
    __table_args__ = (UniqueConstraint('name', 'user_id', name='playlist_user'),)
   
    
class Songs_in_Playlist(db.Model):
    __tablename__ = 'songs_playlist'
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    song = db.relationship('Songs', backref='songs_in_playlist', lazy=True)
    
    
class Album(db.Model):
    __tablename__ = 'albums'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    songs_in_album = db.relationship('Songs_in_Album', backref='album', lazy=True)
    
class Songs_in_Album(db.Model):
    __tablename__ = 'songs_album'
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    song = db.relationship('Songs', backref='songs_in_album', lazy=True)
    
    
class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    song = db.relationship('Songs', backref='ratings', lazy=True)
       
# ------------------------------------------ Models Ends --------------------------------------------------    


################### Load Users ###################
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


################### Index Page ###################
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


############################################# Admin Endpoints ############################################
class Admin:
################### Admin Login ##################
    @app.route('/admin', methods=['GET', 'POST'])
    def admin_login():
        error = None
        #### super-user login username & password ####
        superuser = {'akasharma': 'mad1sept23'}
        
        if request.method == 'GET':
            return render_template('admin_login.html')
        elif request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if username in superuser and superuser[username] == password:
                return redirect(url_for('admin_dash'))
            else:
                error = 'Wrong credentials! Please retry...'
        return render_template('admin_login.html', error=error)


################### Admin Dashboard ###################
    @app.route('/admin/dashboard', methods=['GET'])
    def admin_dash():
        total_users = Users.query.count() # gets total number of users
        total_songs = Songs.query.count() # gets total number of songs
        total_albums = Album.query.count() # gets total number of albums
        # 1st get all genres then keeps only the distinct genre through set 
        genres = [song.genre for song in Songs.query.all()]
        total_genre = len(set(genres))
        # gets the total no of creators after checking if a user is a creator or not
        creators = [user.creator for user in Users.query.all() if user.creator] 
        total_creators = len(creators)
         
        return render_template('admin_dash.html', users=total_users, songs=total_songs,
                               albums=total_albums, genre=total_genre, creators=total_creators)


################### Graphs ###################
# for creator vs avg rating of songs uploaded by them
    creatorRatings = dict() 
    for user in Users.query.filter_by(creator=True).all(): # check if user is a creator
        creator_songs = Songs.query.filter_by(user_id=user.id).all() # gets all the songs uploaded by creators
        # 1st get the ratings of songs and get their average, then do it for all songs uploaded by that
        # particular creator and get the overall average rating
        avg_rating = sum(sum(rating.rating for rating in song.ratings)/len(song.ratings)
                            if song.ratings else 0 for song in creator_songs) / len(creator_songs) if creator_songs else 0
        creatorRatings[user.username] = avg_rating    # maps creator username to avergae rating
    # unzip username and avgRating into seperate list
    creator_usernames, avg_ratings = zip(*creatorRatings.items()) 
    plt.switch_backend('agg')  # Switch the backend of matplotlib to 'agg'
    plt.clf()   # clears current window and makes place for new graph
    fig = plt.figure(figsize=(5, 1.8))
    fig.patch.set_facecolor('none')  # remove backgroud from figure
    plt.bar(creator_usernames, avg_ratings)
    plt.xlabel('Creator Name', color='red')
    plt.ylabel('Song AvgRating', color='blue')
    plt.tight_layout()  # fits label names properly
    plt.savefig('static/graphs/creator_popularity.png')
    
    # for song vs average rating
    songsRatings = dict()
    for song in Songs.query.all():   # loop through all songs
        # calculate average rating for each song
        avg_Rating = sum(rating.rating for rating in song.ratings)/len(song.ratings) if song.ratings else 0
        songsRatings[song.title] = avg_Rating  # store title, avgRating as key, value pair in dict
    song_titles, avg_ratings = zip(*songsRatings.items())  # unpack into seperate list
    plt.switch_backend('agg')  # Switch the backend of matplotlib to 'agg'
    plt.clf()  # clears current window and makes place for new graph
    fig = plt.figure(figsize=(5, 4))
    fig.patch.set_facecolor('none')  # unset backgroud image
    plt.barh(song_titles, avg_ratings)  # creates a horizontal bar chart 
    plt.xlabel('Avg. Rating', color='red')
    plt.ylabel('Song Title', color='blue')
    plt.tight_layout()  # fits label names properly
    song_rating = plt.savefig('static/graphs/song_ratings.png')
    
    
    # for genres vs total songs in it
    genre_counts = dict()
    for song in Songs.query.all():  # loop over all songs
        if song.genre not in genre_counts:  # if genre not in dict then set as 1 else incremenet
            genre_counts[song.genre] = 1
        else:
            genre_counts[song.genre] += 1
    genres, counts = zip(*genre_counts.items())  # unpack into seperate lists
    plt.switch_backend('agg')   # Switch the backend of matplotlib to 'agg'
    plt.clf()  # clears current window and makes place for new graph
    fig = plt.figure(figsize=(5, 1.8))
    fig.patch.set_facecolor('none')  # unset background color
    plt.barh(genres, counts)
    plt.xlabel('Total Songs Count', color='red')
    plt.ylabel('Genre', color='blue')
    plt.tight_layout()
    plt.savefig('static/graphs/genre_counts.png')


################### Admin Search ###################
    @app.route('/admin/search', methods=['GET', 'POST'])
    def admin_search():
        if request.method == 'POST':
            query = request.form['search']
            
            #### for searching songs through title, singer, genre & rating ####
            song_results = [song for song in Songs.query.filter((Songs.title.ilike(f"%{query}%")) | 
                                                                (Songs.singer.ilike(f"%{query}%")) | 
                                                                (Songs.genre.ilike(f"%{query}%")))]
            rating_results = [rating.song for rating in Rating.query.filter(Rating.rating == query)]
            song_results.extend(rating_results)
            
            #### for searching albums through name, artist, genre ####
            album_results = [album for album in Album.query.all() if query.lower() in album.name.lower()]
            album_results.extend([Album.query.get(sia.album_id) for sia in Songs_in_Album.query.join
                                  (Songs).filter((Songs.singer.ilike(f"%{query}%")) |
                                                 (Songs.genre.ilike(f"%{query}%")))])
            # for displaying only distinct albums
            distinct_albums = list(set(album_results))
            
        return render_template('admin_search.html', song_results=song_results, album_results=distinct_albums)


################### View Creators ###################
    @app.route('/admin/view_creators', methods=['GET'])
    def view_creators():
        # gets all users registered as creator
        creators = Users.query.filter(Users.creator==True).all()
        for creator in creators:
            # gets average rating of songs uploaded by creator
            ratings = [rating.rating for rating in creator.ratings]
            creator.avgRating = round(sum(ratings) / len(ratings), 2) if ratings else 0
        return render_template('admin_viewCreator.html', creators=creators)


################### Blacklist/Whitelist Creators ###################
    @app.route('/admin/blacklist/<id>', methods=['GET'])
    def blacklist_creator(id):
        # gets the user through id
        user = Users.query.get(id)
        # if user is not blacklisted but is registered as creator
        if user.blacklisted==False and user.creator==True:
            user.blacklisted = True # mark creator as blacklisted
        else:
            user.blacklisted = False # marks creator as whitlisted
        db.session.commit()
        return redirect(url_for('view_creators'))


################### Manage Tracks ###################
    @app.route('/admin/dashboard/tracks', methods=['GET'])
    def manage_tracks():
        # get all genres
        genres = db.session.query(Songs.genre).distinct().all()
        # get all songs
        songs=Songs.query.order_by(Songs.id.desc()).all()
        return render_template('admin_dash_tracks.html', genres=genres,songs=songs)


################### View Tracks ###################    
    @app.route('/admin/song_details/<id>', methods=['GET'])
    def admin_song(id):
        # gets song by song_id
        song = Songs.query.get(id)
        # gets all ratings for this song
        ratings = [rating.rating for rating in song.ratings]
        # gets average rating for this song
        average_ratings = round(sum(ratings) / len(ratings), 2) if ratings else 0
        return render_template('admin_viewSongs.html', song=song, rating=average_ratings)
    

################### Delete Tracks ###################
    @app.route('/admin/delete_song/<id>', methods=['GET'])
    def admin_delete_tracks(id):
        song = Songs.query.get(id)     
        Songs_in_Album.query.filter_by(song_id=id).delete()  # 1st delter it from Album
        Songs_in_Playlist.query.filter_by(song_id=id).delete()  # then delete it from Playlist
        Rating.query.filter_by(song_id=id).delete()  # then delete all its reatings
        # os.remove(f'./static/audio/{song.filename}') # for deleting filename from ./static/audio
        db.session.delete(song)  # finally delete the song from the database
        db.session.commit()
        return redirect(url_for('manage_tracks'))   
           
        
################### Manage Album ###################
    @app.route('/admin/dashboard/albums', methods=['GET'])
    def manage_albums():
        # gets all the albums and orders them in descending order alphabetically
        albums = Album.query.order_by(Album.id.desc()).all()
        return render_template('admin_dash_albums.html', albums=albums)
    

################### View Album ################### 
    @app.route('/admin/album_detail/<id>', methods=['GET'])
    def admin_album(id):
        album = Album.query.get(id)  # get album through id
        songs_in_album = Songs_in_Album.query.filter_by(album_id=id).all()  # gets all the songs in album
        songs = [song_in_album.song for song_in_album in songs_in_album]  
        error = None
        if not songs:
            error = 'This album is empty.'
        return render_template('admin_viewAlbum.html', album=album, songs=songs, error=error)
    

################### Delete Album ################### 
    @app.route('/admin/delete_album/<id>', methods=['GET'])
    def admin_delete_album(id):
        album = Album.query.get(id)  # gets album id
        Songs_in_Album.query.filter_by(album_id=id).delete()  # 1st delete all songs from album
        db.session.delete(album)  # then delete the album
        db.session.commit()
        return redirect(url_for('manage_albums'))    

# ------------------------------------------ Admin Ends --------------------------------------------------

################### User Registration #################
class Register:
    @app.route('/register', methods=['GET', 'POST'])
    def user_registration():
        error = None
        if request.method == 'GET':
            return render_template('user_registration.html')
        elif request.method == 'POST':
            username=request.form['username']
            email=request.form['email']
            password=request.form['password']
            if Users.query.filter_by(username=username).first() is not None:
                error='Username already exists.'
                return render_template('user_registration.html', error=error)
            if Users.query.filter_by(email=email).first() is not None:
                error='Email already exists.'
                return render_template('user_registration.html', error=error)
            user = Users(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('user_login'))
        return render_template('user_registration.html')
    

############################################# User Endpoints ############################################    
class User:
################### User Login ###################
    @app.route('/user', methods=['GET', 'POST'])
    def user_login():
        error = None
        if request.method == 'GET':
            return render_template('user_login.html')
        elif request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = Users.query.filter_by(username=username).first()
            if user and user.password == password:
                login_user(user)
                return redirect(url_for('user_dash'))
            else:
                error = 'Wrong credentials! Please retry...'
        return render_template('user_login.html', error=error)
 
    
################### User Logout ###################    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))


################### User Dashboard ###################
    @app.route('/user/dashboard', methods=['GET'])
    @login_required
    def user_dash():
        #### for recommended songs ####
        songs=Songs.query.order_by(Songs.id.desc()).all()
        #### for playlist ####
        playlists = Playlist.query.filter_by(user_id=current_user.id).all()
        #### for albums ####
        albums = Album.query.order_by(Album.id.desc()).all()
        #### for genres ####
        genres = db.session.query(Songs.genre).distinct().all()
        return render_template('user_dash.html', songs=songs,genres=genres, playlists=playlists,
                                albums=albums)
    
     
################### Search #################        
    @app.route('/user/search', methods=['GET','POST'])
    @login_required
    def search():
        if request.method == 'POST':
            query = request.form['search']
            
            #### for searching songs through title, singer, genre & rating ####
            song_results = [song for song in Songs.query.filter((Songs.title.ilike(f"%{query}%")) | 
                                                                (Songs.singer.ilike(f"%{query}%")) | 
                                                                (Songs.genre.ilike(f"%{query}%")))]
            rating_results = [rating.song for rating in Rating.query.filter(Rating.rating == query)]
            song_results.extend(rating_results)
            
            #### for searching albums through name, artist, genre ####
            album_results = [album for album in Album.query.all() if query.lower() in album.name.lower()]
            album_results.extend([Album.query.get(sia.album_id) for sia in Songs_in_Album.query.join
                                  (Songs).filter((Songs.singer.ilike(f"%{query}%")) |
                                                 (Songs.genre.ilike(f"%{query}%")))])
            # for displaying only distinct albums
            distinct_albums = list(set(album_results))
        return render_template('search.html', song_results=song_results, album_results=distinct_albums)
        
        
################### View all songs ###################        
    @app.route('/user/songs', methods=['GET'])
    @login_required
    def user_songs():
        songs=Songs.query.order_by(Songs.title).all()
        return render_template('all_songs.html', songs=songs)


################### View Song Details ################### 
    @app.route('/user/song_details/<id>', methods=['GET'])
    @login_required
    def song_details(id):
        song = Songs.query.get(id)
        return render_template('song_detail.html', song=song)


################### Rate Song ################### 
    @app.route('/user/song/rate/<int:id>' , methods=['POST'])
    @login_required
    def rate_songs(id):
        if request.method == 'POST':
            rating = request.form.get('rating')
            if rating:   # if rating for song by same user exits then update it
                existing_rating = Rating.query.filter_by(user_id=current_user.id, song_id=id).first()
                if existing_rating:
                    existing_rating.rating = rating
                else:
                    new_rating = Rating(rating=rating, user_id=current_user.id, song_id=id)
                    db.session.add(new_rating)
                db.session.commit() 
        return redirect(url_for('song_details', id=id))        
        

################### Create Playlist ################### 
    @app.route('/user/create_playlist', methods=['GET', 'POST'])
    @login_required
    def new_playlist():
        if request.method == 'GET':
            songs=Songs.query.all()
            return render_template('new_playlist.html', songs=songs)
        else:
            # get name & lsit of song_id from form
            name = request.form.get('playlist_name')
            song_ids = request.form.getlist('song_ids')
            # add playlist name & user_id to table Playlist
            new_playlist = Playlist(name=name, user_id=current_user.id)
            db.session.add(new_playlist)
            db.session.commit()
            # add songs list to Songs_in_Playlist table
            for song_id in song_ids:
                new_song_in_playlist = Songs_in_Playlist(playlist_id=new_playlist.id, song_id=song_id)
                db.session.add(new_song_in_playlist)
            db.session.commit()
            return redirect(url_for('user_dash'))
       
     
################### View Playlist Songs ###################   
    @app.route('/user/playlist/<id>', methods=['GET'])
    @login_required
    def view_playlist(id):
        playlist = Playlist.query.get(id)
        songs_in_playlist = Songs_in_Playlist.query.filter_by(playlist_id=id).all()
        songs = [song_in_playlist.song for song_in_playlist in songs_in_playlist]
        return render_template('view_playlist.html', playlist=playlist, songs=songs)
 
          
 ################### View Album Songs ###################    
    @app.route('/user/album/<id>', methods=['GET'])
    @login_required
    def view_album(id):
        album = Album.query.get(id)
        songs_in_album = Songs_in_Album.query.filter_by(album_id=id).all()
        songs = [song_in_album.song for song_in_album in songs_in_album]
        error = None
        if not songs:
            error = 'This album is empty.'
        return render_template('view_album.html', album=album, songs=songs, error=error)
     
# ------------------------------------------ User Ends --------------------------------------------------     
          
############################################# Creator Endpoints ##########################################          
    
################### Creator Registration Page ###################         
    @app.route('/user/creator/register', methods=['GET', 'POST'])
    @login_required
    def register_creator():
        if request.method == 'GET':
            return render_template('register_creator.html')
        else:   # POST method to register new creator(handled it from form)
            # check if user has been banned by admin for becoming creator (if not then proceed)
            if current_user.blacklisted == False:
                current_user.creator = True
                db.session.commit()
            else: 
                error = "You have been blacklisted. Plese contact Administrator."
                return render_template('register_creator.html',error=error)
            return redirect(url_for('new_creator'))
    
    
################### New Creator Page (1st page after successful registration 
# also appears when user has not uploaded any songs yet) ###################         
    @app.route('/user/creator/new', methods=['GET'])
    @login_required
    def new_creator():
        # check if user has been banned by admin for becoming creator (if not then proceed)
        if current_user.blacklisted==False:
            return render_template('new_creator.html')
        else:
            return redirect(url_for('register_creator'))
    
    
################### Creator Dashboard ################### 
    @app.route('/user/creator/dashboard', methods=['GET'])
    @login_required
    def creator_dash():
        # check if user has been banned by admin for becoming creator (if not then proceed)
        if current_user.blacklisted==False:
            # for displaying average ratings on dashboard
            ratings = [rating.rating for rating in current_user.ratings]
            average_ratings = round(sum(ratings) / len(ratings), 2) if ratings else 0
            
            return render_template('creator_dash.html', average=average_ratings) 
        else:
            return redirect(url_for('register_creator')) 
    

############################# CREATOR FUNCTIONALITIES ###############################   
 
################### Upload Songs ###################         
    @app.route('/user/creator/song', methods=['GET', 'POST'])
    @login_required
    def upload_songs():
        if request.method == 'GET':
            return render_template('upload_songs.html')
        else:  # performs POST method
            title=request.form['title']
            singer=request.form['singer']
            release_date=request.form['date']
            lyrics=request.form['lyrics']
            genre=request.form['genre']
            file=request.files['file']
            if file: # if valid file with .mp3 extension has been uploaded
                filename = file.filename  # get the filename
            # check if there is no song with same title and singer already available in database
            if Songs.query.filter_by(title=title, singer=singer).first() is None:
                new_song = Songs(title=title, singer=singer, date=release_date, lyrics=lyrics,genre=genre,
                                 user_id=current_user.id, filename=filename)
                # saves audio file to /static/audio
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.session.add(new_song)
                db.session.commit()
                return redirect(url_for('creator_dash'))
            # if a song with same title and singer already exits than display error message
            else:
                error = "Oops, Song already exists!!! Please try changing the song details..."
                return render_template('upload_songs.html',error=error)
    
    
################### Edit Song ###################     
    @app.route('/user/creator/song/edit/<id>', methods=['GET','POST'])
    @login_required
    def edit_song(id):
        song = Songs.query.get(id)
        if request.method == 'GET':
            return render_template('edit_songs.html',song=song)
        else:  # request.method == 'POST'
            title=request.form['title']
            singer=request.form['singer']
            release_date=request.form['date']
            lyrics=request.form['lyrics']
            genre=request.form['genre']
            file=request.files['file']
            if file:  # if valid file with .mp3 extension has been uploaded
                filename = file.filename  # get the filename
            # check if any changes has been made to song, if not then display error   
            if(title==song.title and singer==song.singer and filename==song.filename and release_date==song.date 
               and lyrics==song.lyrics and genre==song.genre):
                error='Please make some changes'
                return render_template('edit_songs.html', error=error,song=song)
            else:  # if changes have been made then proceed further with database
                song.title = title
                song.singer = singer
                song.date = release_date
                song.lyrics = lyrics
                song.genre = genre
                song.filename = filename
                db.session.commit()
                return redirect(url_for('creator_dash')) 
 
     
################### Delete Song  ###################     
    @app.route('/user/creator/delete_song/<id>', methods=['GET'])
    @login_required
    def delete_song(id):
        song = Songs.query.get(id)
        if song.user_id == current_user.id:   # checks if current user is the uploader
            Songs_in_Album.query.filter_by(song_id=id).delete()  # 1st delter it from Album
            Songs_in_Playlist.query.filter_by(song_id=id).delete()  # then delete it from Playlist
            Rating.query.filter_by(song_id=id).delete()  # then delete all its reatings
            # os.remove(f'./static/audio/{song.filename}') # for deleting filename from ./static/audio
            db.session.delete(song)  # finally delete the song from the database
            db.session.commit()
        return redirect(url_for('creator_dash'))   


    
################### Create Album  ###################      
    @app.route('/user/creator/album' , methods=['GET','POST'])
    @login_required
    def create_album():
        if request.method == 'GET':
            songs=Songs.query.all()
            return render_template('create_album.html', songs=songs)
        else:  # request.method == 'POST'
            # gets album name & list of songs from form
            name = request.form.get('album_name')
            song_ids = request.form.getlist('song_ids')
            # add album name & user id to Album table
            new_album = Album(name=name, user_id=current_user.id)
            db.session.add(new_album)
            db.session.commit()
            # add the list of songs to "Songs in Album" table
            for song_id in song_ids:
                new_song_in_album = Songs_in_Album(album_id=new_album.id, song_id=song_id)
                db.session.add(new_song_in_album)
            # finally do commit
            db.session.commit()
            return redirect(url_for('creator_dash'))
        
    
################### Edit Album  ###################    
    @app.route('/user/creator/album/edit/<id>', methods=['GET', 'POST'])
    @login_required
    def edit_album(id):
        album = Album.query.get(id)  # gets album id
        songs = Songs.query.all()    # gets all the songs available in database
        if request.method == 'GET':
        # for getting all currently available songs in album then later displays them as checked in html
            current_song_ids = [song.song_id for song in Songs_in_Album.query.filter_by(album_id=id).all()]
            return render_template('edit_album.html', songs=songs, album=album, 
                                   current_song_ids=current_song_ids)
        else: # request.method == 'POST
            name = request.form.get('album_name')
            #gets song id as str and maps it to int
            song_ids = list(map(int, request.form.getlist('song_ids'))) 
            # gets currently available songs from album
            current_song_ids = [song.song_id for song in Songs_in_Album.query.filter_by(album_id=id).all()]
            # checks if any changes were made, if not then display error message
            if (album.name == name and set(song_ids) == set(current_song_ids)): 
                error='Please make some changes'
                return render_template('edit_album.html', error=error,songs=songs, id=id,
                                       current_song_ids=current_song_ids, album=album)
            else: # if changes were made than proceed with commiting in database
                album.name = name
                Songs_in_Album.query.filter_by(album_id=id).delete() # deletes all previous songs 
                for song_id in song_ids:
                    new_song_in_album = Songs_in_Album(album_id=album.id, song_id=song_id) # adds songs
                    db.session.add(new_song_in_album)
                db.session.commit()
                return redirect(url_for('creator_dash'))


################### Delete Album  ###################                
    @app.route('/user/creator/album/delete/<id>', methods=['GET'])
    @login_required
    def delete_album(id):
        album = Album.query.get(id)  # gets album id
        if album.user_id == current_user.id:  # checks if current user had created the album
            Songs_in_Album.query.filter_by(album_id=id).delete()  # 1st delete all songs from album
            db.session.delete(album)  # then delete the album
            db.session.commit()
        return redirect(url_for('creator_dash')) 
    
# ------------------------------------------ Creator Ends ------------------------------------------------    

    
# checks if this file is the main program being run
if __name__ == '__main__':
    app.run(debug=False, port=1105)
    
    
# --------------------------------------------------------------------------------------------------------   
# ------------------------------------------ The End -----------------------------------------------------    
# ---------------------------------------------------------------------------------------------------------

# Created with ❤️ by AKASH
# Roll no : 22f2000700
# E-mail : 22f2000700@ds.study.iitm.ac.in  |  akasharma.py@gmail.com
# LinkedIn : https://www.linkedin.com/in/aka-sh11
# linktree : https://linktr.ee/akasharma

###########################################################################################################

