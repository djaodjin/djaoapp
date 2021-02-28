/* global $ ace document:true */

function initCodeEditors(api_sources, iframe) {
    "use strict";

    function addPanel(element, name, beforeElem) {
        var tabsContainer = element.find("[role='tablist']");
        var contentsContainer = element.find(".tab-content");
        var idx = tabsContainer.find(">li").length;
        var tab = $("<li class=\"nav-item\"><a class=\"nav-link" + (idx === 0 ? " active" : "") + "\" href=\"#tab-" + idx + "\" data-toggle=\"tab\">" + name + "</a></li>");
        var content = $("<div id=\"tab-" + idx + "\" class=\"tab-pane" + (idx === 0 ? " active" : "") + " role=\"tabpanel\" style=\"width:100%;height:100%;\"><div class=\"content\" data-content=\"" + name + "\" style=\"width:100%;min-height:100%;\"></div></div>");
        if( typeof beforeElem !== 'undefined' ) {
            console.log("insert ", tab, " before", beforeElem);
            beforeElem.before(tab);
        } else {
            tabsContainer.append(tab);
        }
        contentsContainer.append(content);
        content.find(".content").djtemplates({
            api_source_code: api_sources,
            iframe_view: iframe
        });
    };

    var templates = (typeof templateNames !== "undefined" ) ?
        templateNames : [];
    if( typeof iframe !== "undefined" ) {
        templates = iframe.contentWindow.templateNames || [];
    }
    if( templates.length > 0 ) {
        for( var idx = 0; idx < templates.length; ++idx ) {
            addPanel($("#code-editor"), templates[idx].name);
        }
    } else {
        $("#code-editor .tab-content").append("<div>" + gettext('No editable templates') + "</div>");
    }
    $("#code-editor [role='tablist']").append("<li id=\"new-source-btn\" class=\"nav-item\"><a class=\"nav-link\" href=\"#new-source\" data-toggle=\"modal\" data-target=\"#new-source\"><i class=\"fa fa-plus\"></i> New</a></li>");
    $("#code-editor #new-source-submit").click(function(event) {
        event.preventDefault();
        var name = $("#code-editor #new-source [name='name']").val();
        var path = null;
        while( name.length > 0 && name[0] === '/' ) {
            name = name.substr(1);
        }
        if( name.length > 0 && name[name.length - 1] === '/' ) {
            path = name + 'index.html';
        } else {
            path = name + '.html';
        }
        $.ajax({
            url: api_sources + path,
            method: "POST",
            datatype: "json",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify({
                path: path, text: "{% extends \"base.html\" %}\n"}),
            beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", getMetaCSRFToken());
            },
            success: function(){
                // move to new page
                var last = api_sources.indexOf('/api/');
                window.location = api_sources.substr(0, last) + '/' + name;
            },
            error: function(resp) {
                showErrorMessages(resp);
            }
        });
    });
}

(function ($) {
    "use strict";

    /** Template editor
        <div id="#_editor_"></div>
     */
    function TemplateEditor(el, options){
        this.element = el;
        this.$element = $(el);
        this.options = options;
        this.activeFile = "";
        this.init();
    }

    TemplateEditor.prototype = {
        init: function () {
            var self = this;
            self.$element.on("pages.loadresources", function(event) {
                self.loadSource();
            });

            // load ace and extensions
            self.editor = ace.edit(self.element);
            self.editor.setTheme("ace/theme/monokai");
            self.editor.setOption({
                enableEmmet: true,
                enableBasicAutocompletion: true,
                enableSnippets: true,
                enableLiveAutocompletion: false
            });
        },

        loadSource: function(){
            var self = this;
            var path = self.$element.attr("data-content");
            $.ajax({
                url: self.options.api_source_code + path,
                method: "GET",
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(resp){
                    self.editor.setValue(resp.text);
                    var modelist = ace.require("ace/ext/modelist");
                    var path = resp.path;
                    if(path.indexOf('.') !== -1){
                        var chunks = path.split('.').reverse()
                        if(chunks[0] === 'eml'){
                            chunks[0] = 'html'; // treat eml as html
                            path = chunks.reverse().join('.');
                        }
                    }
                    var mode = modelist.getModeForPath(path).mode;
                    self.editor.getSession().setMode(mode);
                    self.editor.focus();
                    self.editor.gotoLine(0);
                    self.editor.on("change", $.debounce( 250, function() {
                        self.saveSource();
                    }));
                },
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        },

        saveSource: function(){
            var self = this;
            var path = self.$element.attr("data-content");
            self.$element.trigger('pages.save');
            $.ajax({
                url: self.options.api_source_code + path,
                method: "PUT",
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                data: JSON.stringify({
                    path: path, text: self.editor.getValue()}),
                beforeSend: function(xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", getMetaCSRFToken());
                },
                success: function(){
                    // reload content
                    if ( self.options.iframe_view ){
                        self.options.iframe_view.src = self.options.iframe_view.src;
                    }
                },
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        }

    };

    $.fn.djtemplates = function(options) {
        var opts = $.extend( {}, $.fn.djtemplates.defaults, options );
        return this.each(function() {
            if (!$.data($(this), "djtemplates")) {
                $.data($(this), "djtemplates", new TemplateEditor(this, opts));
            }
        });
    };

    $.fn.djtemplates.defaults = {
        api_source_code: "/api/source"
    };

})(jQuery);
