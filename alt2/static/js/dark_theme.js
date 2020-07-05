function dark_toggle() {
    var el1 = document.getElementById("dark-reader");
    var icon = document.getElementById("dark-reader-icon");
    if(el1.disabled) {
        el1.disabled = false;
        icon.setAttribute("class", "fas fa-sun fa-pulse");
        localStorage.setItem("darkreader", "enabled");
    } else {
        el1.disabled = true;
        icon.setAttribute("class", "fas fa-moon fa-pulse");
        localStorage.setItem("darkreader", "disabled");
    }
}