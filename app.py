# -*- coding: utf-8 -*- 
import os
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8' 

from flask import Flask, render_template, request, make_response
import json
import cx_Oracle
import math
import markdown2
import re

app = Flask(__name__)

@app.route('/')
@app.route('/<int:page>')
def home(page=1):
	sql = "select count(*) from blog"
	count = sql_select_execute(sql)[0][0]
	sql = "select * from (select rownum rn, id, title, author_id, content from (select id, title, author_id, content from blog order by created_at desc) where rownum <= " + str(page * 5) + ") blog2 where blog2.rn >=" + str((page - 1) * 5 + 1)
	blogs = sql_select_execute(sql)
	result = []
	for blog in blogs:
		id = blog[1]
		title = blog[2]
		author = sql_select_execute("select * from users where id=" + str(blog[3]))[0][1]
		content = blog[4][0:100] + "..."
		result.append((id, author, title, content))
	return render_template('home.html', blogs=result, page=page, pages=math.ceil(count/5))

@app.route('/blog/<int:id>')
def blog(id):
	sql = "select * from blog where id=" + str(id)
	blog = sql_select_execute(sql)
	title = blog[0][3]
	author = sql_select_execute("select * from users where id=" + str(blog[0][1]))[0][1]
	content = markdown2.markdown(blog[0][4])
	category = sql_select_execute("select * from category where id=" + str(blog[0][2]))[0][1]
	tags = sql_select_execute("select tag.name from blog_tag, tag where blog_tag.tag_id=tag.id and blog_tag.blog_id=" + str(blog[0][0]))
	comments = sql_select_execute("select users.username, comments.content from comments, users where comments.author_id=users.id and comments.blog_id=" + str(id))
	result = (id, author, title, content, category, tags, comments)
	return render_template("blog.html", blog=result)

@app.route('/myblog')
@app.route('/myblog/<int:id>')
def myblog(page=1):
	author_id = request.args.get('author_id')
	sql = "select count(*) from blog where author_id=" + str(author_id)
	count = sql_select_execute(sql)[0][0]
	sql = "select * from (select rownum rn, id, title, author_id, content from (select id, title, author_id, content from blog where author_id=" + str(author_id) + "order by created_at desc) where rownum <= " + str(page * 5) + ") blog2 where blog2.rn >=" + str((page - 1) * 5 + 1)
	blogs = sql_select_execute(sql)
	result = []
	for blog in blogs:
		id=blog[1]
		title = blog[2]
		author = sql_select_execute("select * from users where id=" + str(blog[3]))[0][1]
		content = blog[4][0:100] + "..."
		# category = sql_select_execute("select * from category where id=" + str(blog[0][2]))[0][1]
		# tags = sql_select_execute("select tag.name from blog_tag, tag where blog_tag.tag_id=tag.id and blog_tag.blog_id=" + str(blog[0][0]))
		# comments = sql_select_execute("select users.username, comments.content from comments, users where comments.author_id=users.id and comments.blog_id=" + str(id))
		result.append((id, author, title, content))
	return render_template("myblog.html", blogs=result, count=count, page=page, pages=math.ceil(count/5))

@app.route('/deleteblog', methods=['POST'])
def deleteblog():
	blog_id = request.form['blog_id']
	print(blog_id)
	sql = "delete from blog where id=" + str(blog_id)
	sql_delete_execute(sql)
	result = {"status": "success"}
	return json.dumps(result)

@app.route('/editblog/<int:id>', methods=['GET', 'POST'])
def editblog(id):
	if request.method == 'GET':
		sql = "select * from blog where id=" + str(id)
		blog = sql_select_execute(sql)
		title = blog[0][3]
		author = sql_select_execute("select * from users where id=" + str(blog[0][1]))[0][1]
		content = blog[0][4]
		category = sql_select_execute("select * from category")
		tag = sql_select_execute("select * from tag")
		selected_category = sql_select_execute("select * from category where id=" + str(blog[0][2]))[0][0]
		selected_tags = sql_select_execute("select tag.id from blog_tag, tag where blog_tag.tag_id=tag.id and blog_tag.blog_id=" + str(blog[0][0]))
		selected_tags_result = []
		for selected_tag in selected_tags:
			selected_tags_result.append(selected_tag[0])
		result = (id, title, author, content, selected_category, selected_tags_result)
		return render_template("editblog.html", categories=category, tags=tag, blog=result)
	else:
		author_id = request.form['author_id']
		title = request.form['title']
		content = request.form['content']
		category = request.form['category']
		tags = request.form.getlist('tags')
		print(tags)
		selected_tags = sql_select_execute("select tag.id from blog_tag, tag where blog_tag.tag_id=tag.id and blog_tag.blog_id=" + str(id))
		sql = "delete from blog_tag where blog_id=" + str(id)
		sql_delete_execute(sql)
		sql = "update blog set author_id = " + str(author_id) + ", title = '" + str(title) + "', content = '" + str(content) + "', category_id = " + str(category) + " where id=" + str(id)
		sql_update_execute(sql)
		for tag in tags:
			sql_insert_execute("insert into blog_tag (blog_id, tag_id) values (" + str(id) + ", " + str(tag) + ")")
		result = {"status": "success"}
		return json.dumps(result) 

@app.route('/addcomment', methods=['POST'])
def addcomment():
	author_id = request.form['author_id']
	blog_id = request.form['blog_id']
	content = request.form['content']
	print(author_id)
	print(blog_id)
	print(content)
	sql = "insert into comments(author_id, blog_id, content, created_at, edited_at) values (" + str(author_id) + ", " + str(blog_id) + ", '" + str(content) + "', sysdate, sysdate)"
	sql_insert_execute(sql)
	result = {"status": "success"}
	return json.dumps(result)
	
@app.route('/signin', methods=['POST', 'GET'])
def signin():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		sql = "select * from users where username='" + username + "' and password='" + password +"'"
		select_result = sql_select_execute(sql)
		is_valid_login = len(select_result) == 0
		if (not is_valid_login):
			result = {'status': 'success', 'user_id': select_result[0][0]}
			return json.dumps(result)
		else:
			result = {'status': 'failed', 'error_msg': '用户名密码错误'}
			return json.dumps(result)
	else:
		return render_template('signin.html')

@app.route('/signup', methods=['POST', 'GET'])
def signup():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		sql = "select * from users where username='" + username + "'"
		is_username_existed = len(sql_select_execute(sql)) == 0
		if (is_username_existed):
			sql_insert_execute("insert into users(username, password) values ('" + username + "', '" + password + "')")
			select_result = sql_select_execute("select * from users where username='" + username + "'")
			result = {'status': 'success', 'user_id': select_result[0][0]}
			return json.dumps(result)
		else:
			result = {'status': 'failed', 'error_msg': '用户名已存在'}
			return json.dumps(result)
	else:
		return render_template('signup.html')

@app.route('/newblog', methods=['POST', 'GET'])
def newblog():
	if request.method == 'POST':
		author_id = request.form['author_id']
		title = request.form['title']
		content = request.form['content']
		category = request.form['category']
		tags = request.form.getlist('tags')
		sql_insert_execute("insert into blog (author_id, title, content, category_id, created_at, edited_at) values (" + author_id + ", '" + title + "', '" + content + "', " + category + ", sysdate, sysdate)")
		select_result = sql_select_execute("select * from blog where title='" + title + "'")
		blog_id = select_result[0][0]
		for tag in tags:
			sql_insert_execute("insert into blog_tag (blog_id, tag_id) values (" + str(blog_id) + ", " + str(tag) + ")")
		result = {'status': 'success'}
		return json.dumps(result)
	else:
		category = sql_select_execute("select * from category")
		tag = sql_select_execute("select * from tag")
		print(category)
		return render_template('newblog.html', categories=category, tags=tag)

@app.route('/addcategory', methods=['POST'])
def addcategory():
	name = request.form['name']
	sql_insert_execute("insert into category (name) values ('" + name + "')")
	select_result = sql_select_execute("select * from category where name='" + name + "'")
	result = {'status': 'success', 'category_id': select_result[0][0]}
	return json.dumps(result)

@app.route('/addtag', methods=['POST'])
def addtag():
	name = request.form['name']
	sql_insert_execute("insert into tag (name) values ('" + name + "')")
	select_result = sql_select_execute("select * from tag where name='" + name +"'")
	result = {'status': 'success', 'tag_id': select_result[0][0]}
	return json.dumps(result)

@app.route('/categories')
@app.route('/categories/<int:id>')
def categories(id=0):
	select_result = sql_select_execute("select * from category")
	if (id == 0):
		return render_template("categories.html", categories=select_result) 
	else:
		sql = "select * from blog where category_id=" + str(id)
		blogs = sql_select_execute(sql)
		result = []
		for blog in blogs:
			blog_id=blog[0]
			title = blog[3]
			author = sql_select_execute("select * from users where id=" + str(blog[1]))[0][1]
			content = blog[4][0:100] + "..."
			result.append((id, blog_id, author, title, content))
		return render_template("categories.html", categories=select_result, selected_category=id, blogs=result)

@app.route('/tags')
@app.route('/tags/<int:id>')
def tags(id=0):
	select_result = sql_select_execute("select * from tag")
	if (id == 0):
		return render_template("tags.html", tags=select_result)
	else:
		sql = "select blog.* from blog, blog_tag where blog.id=blog_tag.blog_id and blog_tag.tag_id=" + str(id)
		blogs = sql_select_execute(sql)
		result = []
		for blog in blogs:
			blog_id=blog[0]
			title = blog[3]
			author = sql_select_execute("select * from users where id=" + str(blog[1]))[0][1]
			content = blog[4][0:100] + "..."
			result.append((id, blog_id, author, title, content))
		print(id)
		return render_template("tags.html", tags=select_result, selected_tag=id, blogs=result)

def sql_insert_execute(sql):
	db = cx_Oracle.connect('system', 'm1234', '111.231.116.162:1521/XE')
	cur = db.cursor()
	cur.prepare(sql)
	cur.execute(None)
	db.commit()
	cur.close()
	db.close()

def sql_select_execute(sql):
	db = cx_Oracle.connect('system', 'm1234', '111.231.116.162:1521/XE')
	cur = db.cursor()
	cur.prepare(sql)
	row = cur.execute(None).fetchall()
	cur.close()
	db.close()
	return row

def sql_delete_execute(sql):
	db = cx_Oracle.connect('system', 'm1234', '111.231.116.162:1521/XE')
	cur = db.cursor()
	cur.prepare(sql)
	cur.execute(None)
	db.commit()
	cur.close()
	db.close()

def sql_update_execute(sql):
	db = cx_Oracle.connect('system', 'm1234', '111.231.116.162:1521/XE')
	cur = db.cursor()
	cur.prepare(sql)
	cur.execute(None)
	db.commit()
	cur.close()
	db.close()