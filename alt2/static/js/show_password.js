document.querySelectorAll('.password-toggle').forEach(function(toggle) {
    toggle.addEventListener('click', function() {
        const input = document.getElementById(this.dataset.target);
        const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
        input.setAttribute('type', type);
        this.querySelector('i').classList.toggle('ion-ios-eye');
        this.querySelector('i').classList.toggle('ion-ios-eye-off');
    });
});
