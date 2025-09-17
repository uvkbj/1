from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)
'''
if __name__ == '__main__':
    with app.app_context():
        print("==== Registered Routes ====")
        for rule in app.url_map.iter_rules():
            print(rule)
    app.run(debug=True)
'''