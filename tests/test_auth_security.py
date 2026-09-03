def test_unknown_email_and_wrong_password_share_generic_message(client):
    known = client.post(
        "/admin/login",
        data={"email": "admin@example.com", "password": "wrong-password"},
    )
    unknown = client.post(
        "/admin/login",
        data={"email": "unknown@example.com", "password": "wrong-password"},
    )
    message = "بيانات تسجيل الدخول غير صحيحة"
    assert message in known.text
    assert message in unknown.text
