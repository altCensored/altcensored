// show_password.js
const togglePassword = document.querySelector('#togglePassword');
const password = document.querySelector('#password');

togglePassword.addEventListener('click', function (e) {
    // toggle the type attribute
    const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
    password.setAttribute('type', type);
    // toggle the eye / eye slash icon
    this.querySelector('i').classList.toggle('ion-ios-eye');
    this.querySelector('i').classList.toggle('ion-ios-eye-off');
});