function addScript(src, onload){
    var doc = window.document;
    if( src.substr(-4) === ".css" ) {
        var script = doc.createElement("link");
        script.rel = "stylesheet";
        script.type = "text/css"
        script.href = src;
        doc.body.appendChild(script);
    } else {
        var script = doc.createElement("script");
        script.type = "text/javascript";
        if( src[0] == "/" ) {
            script.src = src;
        } else {
            script.text = src;
        }
        doc.body.appendChild(script);
    }
    script.onload = onload;
};

function loadNext(){
    if ( window.edition_sources.length > 0 ){
        var src = window.edition_sources.shift();
        addScript(src, loadNext);
    }
}
loadNext();
