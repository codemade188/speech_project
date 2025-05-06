from flask import Flask


from app import create_app

app = create_app()


@app.route('/')
def hello_world():  # put application's code here
    return '这是flask开发的英语口语学习项目'


if __name__ == "__main__":
    app.run()





