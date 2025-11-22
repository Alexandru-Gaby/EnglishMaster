from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 EnglishMaster pornește pe http://localhost:5000")
    print("📝 Pagini disponibile:")
    print("   - http://localhost:5000/")
    print("   - http://localhost:5000/register")
    print("   - http://localhost:5000/login")
    print("\n Apasă CTRL+C pentru a opri serverul\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)