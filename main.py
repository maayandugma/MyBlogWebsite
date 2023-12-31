from flask import Flask, render_template, redirect, url_for, flash,request,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from functools import wraps
from flask_gravatar import Gravatar
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
secret_key = os.environ.get('SECRET_KEY')
app.config['SECRET_KEY'] = secret_key
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")


class User(db.Model,UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comment = relationship("Comment",back_populates="comment_author")

class Comment(db.Model,UserMixin):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship('User', back_populates="comment")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

# db.create_all()
gravatar = Gravatar(
    app, size=100, rating='g', default='retro', force_default=False,
     use_ssl=False, base_url=None
)


@app.route('/posts')
def get_all_posts():
    posts = BlogPost.query.all()

    return render_template("index.html", all_posts=posts,current_user=current_user,logged_in=current_user.is_authenticated)


@app.route('/register',methods=["POST","GET"])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if User.query.filter_by(email=request.form["email"]).first():
                flash("You've already signed up with that email, log in instead!")
                return redirect(url_for('login'))

            hash_and_salted_password = generate_password_hash(
                password=request.form.get("password"),
                method="sha256",
                salt_length=8
                )
            email = request.form.get("email")
            name = request.form.get("name")
            new_user = User()
            new_user.email = email
            new_user.password = hash_and_salted_password
            new_user.name = name
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            return redirect(url_for("get_all_posts"))

    return render_template("register.html",form=form,logged_in=current_user.is_authenticated)

@app.route('/',methods=["POST","GET"])
@app.route('/login',methods=["POST","GET"])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data

            user = User.query.filter_by(email=email).first()
            if not user:
                flash("That email doesn't exist, please try again")
                return redirect(url_for('login'))
            elif not check_password_hash(user.password,password):
                flash("Password incorrect, please try again")
                return redirect(url_for('login'))
            else:
                login_user(user)
                return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=form,logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


def admin_only(f):
    @wraps(f)
    def decorate_function(*args,**kwargs):
        if current_user.id != 1:
            return abort(403)
        else:
            return f(*args, **kwargs)

    return decorate_function


@app.route("/new-post",methods=["POST","GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,logged_in=current_user.is_authenticated,author=current_user)


@app.route("/edit-post/<int:post_id>",methods=["POST","GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/post/<int:post_id>",methods=["POST","GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()
    if request.method =="POST":
        if comment_form.validate_on_submit():
            new_comment = Comment(
                text = comment_form.comment_text.data,
                parent_post = requested_post,
                comment_author = current_user
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post',post_id=post_id))
    return render_template("post.html", post=requested_post,form=comment_form,logged_in=current_user.is_authenticated)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True)
