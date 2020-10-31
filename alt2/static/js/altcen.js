function add_video_WatchLater(vid){
    fetch('{{ url_for('user.add_video_watchlater_post') }}', {
      method: 'POST',
      body: JSON.stringify({
        'v': vid
      })
    })
    var ttip = "ttip"
    var ttipid = ttip.concat(vid);
    var watchlaterIcon = document.getElementById(vid);
    watchlaterIcon.className="ion-md-checkmark";
    var tooltip = watchlaterIcon.parentNode.parentNode.querySelector('.tooltip');
    tooltip.style.display = 'none';
}
