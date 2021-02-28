/**
   Functionality related to the wysiwyg editor in djaodjin-pages.

   These are based on jquery.
 */

/* global location setTimeout jQuery */
/* global getMetaCSRFToken showMessages */

(function ($) {
    "use strict";
    var preventClick = false;

    function BaseEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    BaseEditor.prototype = {
        init: function(){
            var self = this;
        },

        _getCSRFToken: function() {
            var self = this;
            var crsfNode = self.el.find("[name='csrfmiddlewaretoken']");
            if( crsfNode.length > 0 ) {
                return crsfNode.val();
            }
            return getMetaCSRFToken();
        },

        getId: function() {
            var self = this;
            var slug = self.$el.attr(self.options.uniqueIdentifier);
            if( !slug ) {
                slug = self.$el.parents(
                    "[" + self.options.uniqueIdentifier + "]").attr(
                        self.options.uniqueIdentifier);
            }
            if( !slug ) {
                slug = "undefined";
            }
            return slug;
        },

        elementUrl: function() {
            var self = this;
            var path = self.getId();
            if( path.indexOf('/') != 0 ) path = '/' + path
            return self.options.baseUrl + path;
        },

        addTags: function(tags) {
            var self = this;
            $.ajax({
                method: "PUT",
                url: self.elementUrl() + "/add-tags/",
                beforeSend: function(xhr) {
                    xhr.setRequestHeader("X-CSRFToken", self._getCSRFToken());
                },
                data: JSON.stringify({"tag": tags}),
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(resp) {
                    self.options.onSuccess(self, resp);
                },
                error: self.options.onError
            });
        },

        removeTags: function(tags) {
            var self = this;
            $.ajax({
                method: "PUT",
                url: self.elementUrl() + "/remove-tags/",
                beforeSend: function(xhr) {
                    xhr.setRequestHeader("X-CSRFToken", self._getCSRFToken());
                },
                data: JSON.stringify({"tag": tags}),
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(resp) {
                    self.options.onSuccess(self, resp);
                },
                error: self.options.onError
            });
        },
    };

    $.fn.baseEditor = function(options, custom){
        var opts = $.extend( {}, $.fn.baseEditor.defaults, options );
        return this.each(function() {
            console.log("attach editor to", this);
            $(this).data("editor", new BaseEditor($(this), opts));
        });
    };

    $.fn.baseEditor.defaults = {
        baseUrl: null, // Url to send request to server
        uniqueIdentifier: "id",
        onSuccess: function(element, resp){
            return true;
        },
        onError: function(resp){
            showErrorMessages(resp);
        },
    };

    /**
     */
    function Editor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    Editor.prototype = $.extend({}, BaseEditor.prototype, {
        init: function(){
            var self = this;
            self.$el.on("click", function(){
                self.toggleEdition();
            });
            self.$el.on("blur", function(){
                self.saveEdition();
            });
            self.$el.on("mouseover mouseleave", function(event){
                self.hoverElement(event);
            });

            $(".editable").bind("hallomodified", function(event, data) {
                $("#modified").html(gettext("Editables modified"));
            });
            if (self.options.preventBlurOnClick !== ""){
                $(document).on("mousedown", self.options.preventBlurOnClick, function(event){
                    event.stopPropagation();
                    preventClick = true;
                });
            }
            if( self.options.focus ) {
                self.toggleEdition();
            }
        },

        hoverElement: function(event){
            var self = this;
            if (event.type === "mouseover"){
                self.$el.addClass("hover-editable");
            }else{
                self.$el.removeClass("hover-editable");
            }
        },

        getOriginText: function(){
            var self = this;
            self.originText = $.trim(self.$el[0].outerHTML);
            return self.originText;
        },

        toogleStartOptional: function(){
            return true;
        },

        toogleEndOptional: function(){
            return true;
        },

        initHallo: function(){
            var self = this;
            self.$el.hallo().focus();
        },

        toggleEdition: function(){
            var self = this;
            self.initHallo();
            self.getOriginText();
            self.$el.attr("placeholder", self.options.emptyInputText);
        },

        getSavedText: function(){
            var self = this;
            return $.trim(self.$el.html());
        },

        checkInput: function(){
            var self = this;
            if (self.getSavedText() === ""){
                return false;
            }else{
                return true;
            }
        },

        formatDisplayedValue: function(){
            return true;
        },

        saveEdition: function(){
            var self = this;
            if( !self.checkInput() ) {
                return false;
            }

            var data = {};
            var method = "PUT";
            var savedText = self.getSavedText();
            if (self.$el.attr("data-key")){
                data[self.$el.attr("data-key")] = savedText;
            } else {
                data = {
                    slug: self.getId(),
                    text: savedText
                };
            }

            if( self.options.debug ){
                console.log("data-key:", self.$el.attr("data-key"),
                    "send:", data);
            }
            $.ajax({
                method: method,
                url: self.elementUrl(),
                beforeSend: function(xhr) {
                    xhr.setRequestHeader("X-CSRFToken", self._getCSRFToken());
                },
                data: JSON.stringify(data),
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(resp) {
                    self.options.onSuccess(self, resp);
                    self.$el.removeAttr("contenteditable");
                    self.formatDisplayedValue();
                },
                error: self.options.onError
            });
        }
    });

    function CurrencyEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    CurrencyEditor.prototype = $.extend({}, Editor.prototype, {
        getSavedText: function(){
            var self = this;
            var enteredValue = self.$el.text();
            var amount = parseInt(
                (parseFloat(enteredValue.replace(/[^0-9\.]+/g, "")) * 100).toFixed(2));
            return amount;
        },

        formatDisplayedValue: function(){
            var self = this;
            var defaultCurrencyUnit = "$";
            var defaultCurrencyPosition = "before";
            if (self.$el.data("currency-unit")){
                defaultCurrencyUnit = self.$el.data("currency-unit");
            }

            if (self.$el.data("currency-position")){
                defaultCurrencyPosition = self.$el.data("currency-position");
            }

            var amount = String((self.getSavedText() / 100).toFixed(2));
            if (defaultCurrencyPosition === "before"){
                amount = defaultCurrencyUnit + amount;
            }else if(defaultCurrencyPosition === "after"){
                amount = amount + defaultCurrencyUnit;
            }
            self.$el.html(amount);
        }
    });

    function FormattedEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    FormattedEditor.prototype = $.extend({}, Editor.prototype, {
        initHallo: function(){
            var self = this;
            self.$el.hallo({
                plugins: {
                    "halloheadings": {},
                    "halloformat": {},
                    "halloblock": {},
                    "hallojustify": {},
                    "hallolists": {},
                    "hallolink": {},
                    "halloreundo": {}
                },
                editable: true,
                toolbar: "halloToolbarFixed"
            }).focus();
            self.initDroppable();
        },

        // method only applicable
        initDroppable: function(){
            // Build our own droppable to avoid useless features
            var self = this;
            $.each(self.$el.children(), function(index, element){
                if (!$(element).hasClass("ui-droppable")){
                    $(element).droppable({
                        drop: function(){
                            var droppable = $(this);
                            droppable.focus();
                        },
                        over: function(event, ui){
                            var droppable = $(this);
                            var draggable = ui.draggable;
                            droppable.append("<img src=\"" + draggable.attr("src") + "\" style=\"max-width:100%;\">");
                        },
                        out: function(event, ui){
                            var draggable = ui.draggable;
                            $(this).children("[src=\"" + draggable.attr("src") + "\"]").remove();
                        }
                    });
                }
            });
        }
    });

    function MarkdownEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    MarkdownEditor.prototype = $.extend({}, Editor.prototype, {

        markdownTools: function(){
            var self = this;
            self.$mardownToolHtml = $("<div id=\"markdown_tool_" + self.getId() + "\" class=\"" + self.options.container_tool_class + "\">\
                                <button type=\"button\" class=\"" + self.options.btn_tool_class + " markdown-h3\">H3</button>\
                                <button type=\"button\" class=\"" + self.options.btn_tool_class + " markdown-h4\">H4</button>\
                                <button type=\"button\" class=\"" + self.options.btn_tool_class + " markdown-bold\"><strong>B</strong></button>\
                                <button type=\"button\" class=\"" + self.options.btn_tool_class + " markdown-italic\"><em>I</em></button>\
                                <button type=\"button\" class=\"" + self.options.btn_tool_class + " markdown-list-ul\">List</button>\
                                <button type=\"button\" class=\"" + self.options.btn_tool_class + " markdown-link\">Link</button></div>");
            return self.$mardownToolHtml;
        },

        textArea: function(){
            var self = this;
            self.$textarea = $("<textarea placeholder=\"" + self.options.emptyInputText + "\" class=\"djaodjin-editor\" id=\"textarea_" + self.getId() + "\" style=\"\"></textarea>");
            return self.$textarea;
        },

        getElementProperties: function(){
            var self = this;
            if (self.$el.prop("tagName") === "DIV"){
                if (self.$el.children("p").length > 0){
                    return self.$el.children("p");
                }else{
                    return $("p");
                }
            }else{
                return self.$el;
            }
        },

        getProperties: function(){
            var self = this;
            self.classElement = self.$el.attr("class");
            var element = self.getElementProperties();
            self.cssVar = {
                "font-size": element.css("font-size"),
                "line-height": element.css("line-height"),
                "height": parseInt(element.css("height").split("px")) + (parseInt(element.css("line-height").split("px")) - parseInt(element.css("font-size").split("px"))) + "px",
                "margin-top": element.css("margin-top"),
                "font-family": element.css("font-family"),
                "font-weight": element.css("font-weight"),
                "text-align": element.css("text-align"),
                "padding-top": -(parseInt(element.css("line-height").split("px")) - parseInt(element.css("font-size").split("px"))) + "px",
                "color": element.css("color"),
                "width": element.css("width")
            };
        },

        toggleEdition: function(){
            var self = this;
            setTimeout(function(){
                self.getOriginText();
                self.initEditor();
            }, self.options.delayMarkdownInit);

        },

        initEditor: function(){
            var self = this;
            self.getProperties();
            self.markdownTools();
            $("body").append(self.$mardownToolHtml);
            self.$mardownToolHtml.css({
                top: (self.$el.offset().top - 45) + "px",
                left: self.$el.offset().left + "px"
            });
            self.$el.replaceWith(self.textArea());
            self.$textarea.css(self.cssVar).val(self.originText).textareaAutoSize().focus();
            if (!self.eventAttached){
                $("body").on("blur", "#" + self.$textarea.attr("id"), function(){
                    if (!preventClick){
                        self.saveEdition();
                    }else{
                        $("#" + self.$textarea.attr("id")).focus();
                        preventClick = false;
                    }
                });
                $("body").on("mousedown", "#" + self.$mardownToolHtml.attr("id"), function(event){
                    event.preventDefault();
                    var $target = $(event.target);
                    if ($target.hasClass("markdown-h3")){
                        $("#" + self.$textarea.attr("id")).selection("insert", {text: "###", mode: "before"}).selection("insert", {text: "", mode: "after"});
                    }else if($target.hasClass("markdown-h4")){
                        $("#" + self.$textarea.attr("id")).selection("insert", {text: "####", mode: "before"}).selection("insert", {text: "", mode: "after"});
                    }else if($target.hasClass("markdown-bold")||$target.parent().hasClass("markdown-bold")){
                        $("#" + self.$textarea.attr("id")).selection("insert", {text: "**", mode: "before"}).selection("insert", {text: "**", mode: "after"});
                    }else if($target.hasClass("markdown-list-ul")){
                        $("#" + self.$textarea.attr("id")).selection("insert", {text: "* ", mode: "before"}).selection("insert", {text: "", mode: "after"});
                    }else if($target.hasClass("markdown-link")){
                        var text = $("#" + self.$textarea.attr("id")).selection();
                        if (text.indexOf("http://") >= 0){
                            $("#" + self.$textarea.attr("id")).selection("insert", {text: "[" + text + "](", mode: "before"}).selection("insert", {text: ")", mode: "after"});
                        }else{
                            $("#" + self.$textarea.attr("id")).selection("insert", {text: "[http://" + text + "](http://", mode: "before"}).selection("insert", {text: ")", mode: "after"});
                        }
                    }else if($target.attr("id") === "italic"){
                        $("#" + self.$textarea.attr("id")).selection("insert", {text: "*", mode: "before"}).selection("insert", {text: "*", mode: "after"});
                    }
                });
            }
            $("#" + self.$textarea.attr("id")).droppable({
                drop: function(event, ui){
                    var droppable = $(this);
                    var draggable = ui.draggable;
                    droppable.focus();
                    droppable.selection("insert", {
                        text: "![Alt text](" + draggable.attr("src") + ")",
                        mode: "before"
                    });
                    $(ui.helper).remove();
                }
            });
            self.eventAttached = true;
        },

        getSavedText: function(){
            var self = this;
            return $.trim(self.$textarea.val());
        },

        formatDisplayedValue: function(){
            var self = this;
            var convert = new Markdown.getSanitizingConverter().makeHtml;
            var newHtml = convert(self.getSavedText()).replace("<img ", "<img style=\"max-width:100%\" ");
            self.$textarea.replaceWith(self.$el.html(newHtml));
            self.$textarea.remove();
            self.$mardownToolHtml.remove();
            self.init();
        },

        getOriginText: function(){
            var self = this;
            self.originText = "";
            if (self.options.baseUrl){
                $.ajax({
                    method: "GET",
                    url: self.elementUrl(),
                    contentType: "application/json; charset=utf-8",
                    beforeSend: function(xhr) {
                        xhr.setRequestHeader("X-CSRFToken", self._getCSRFToken());
                    },
                    async: false,
                    success: function(data){
                        if (self.$el.attr("data-key")){
                            self.originText = data[self.$el.attr("data-key")];
                        }else{
                            self.originText = data.text;
                        }
                    },
                    error: function(){
                        self.originText = $.trim(self.$el.text());
                    }
                });
            }
            return self.originText;
        }

    });

    function RangeEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    RangeEditor.prototype = $.extend({}, Editor.prototype, {
        valueSelector: function(){
            var self = this;
            self.$valueSelector = $("<input class=\"djaodjin-editor\" id=\"value_selector_" + self.getId() + "\" style=\"width:auto;\"/ type=\"range\">");

            self.$valueSelector.on("input", function(event){
                var val = $(this).val();
                event.stopPropagation();
                self.options.rangeUpdate(self.$el, val);
                if (self.$el.data("range-value") !== "undefined"){
                    self.$el.data("range-value", val);
                }
            });

            self.$valueSelector.on("mouseup", function(event){
                self.$valueSelector.blur();
            });

            self.$valueSelector.on("blur", function(event){
                self.saveEdition();
                self.$valueSelector.remove();
                self.$valueSelector = null;
                event.stopPropagation();
            });

            return self.$valueSelector;
        },

        getOriginText: function(){
            var self = this;
            if (self.$el.data("range-value") !== "undefined"){
                self.originText = self.$el.data("range-value");
            }else{
                self.originText = $.trim(self.$el.text());
            }
            return self.originText;
        },

        getSavedText: function(){
            var self = this;
            var newVal = self.$valueSelector.val();
            var values = self.$el.data("range-values");
            if (values){
                if (values[String(newVal)]){
                    newVal = values[String(newVal)];
                }
            }
            return newVal;
         },

        toggleEdition: function(){
            var self = this;
            if (self.$valueSelector){
                self.$valueSelector.blur();
            }else{
                self.getOriginText();
                self.$el.append(self.valueSelector());
                self.$valueSelector.attr("min", self.$el.data("range-min"))
                    .attr("max", self.$el.data("range-max"))
                    .attr("step", self.$el.data("range-step"))
                    .val(self.originText).css({
                        position: "absolute",
                        width: self.$el.outerWidth(),
                        left: self.$el.offset().left + "px"
                    });

                if (self.options.rangePosition === "middle"){
                    self.$valueSelector.css({top: (self.$el.offset().top + (self.$el.height() / 2)) + "px"});
                }else if (self.options.rangePosition === "bottom"){
                    self.$valueSelector.css({top: (self.$el.offset().top + self.$el.height()) + "px"});
                }else if (self.options.rangePosition === "top"){
                    self.$valueSelector.css({top: self.$el.offset().top + "px"});
                }
                self.$valueSelector.focus();
            }
        }
    });

    $.fn.editor = function(options, custom){
        var opts = $.extend( {}, $.fn.editor.defaults, options );
        return this.each(function() {
            if (!$.data($(this), "editor")) {
                if ($(this).hasClass("edit-formatted")){
                    $.data($(this), "editor", new FormattedEditor($(this), opts));
                }else if ($(this).hasClass("edit-markdown")){
                    $.data($(this), "editor", new MarkdownEditor($(this), opts));
                }else if ($(this).hasClass("edit-currency")){
                    $.data($(this), "editor", new CurrencyEditor($(this), opts));
                }else if ($(this).hasClass("edit-range")){
                    $.data($(this), "editor", new RangeEditor($(this), opts));
                }else{
                    $.data($(this), "editor", new Editor($(this), opts));
                }
            }
        });
    };

    $.fn.editor.defaults = {
        baseUrl: null, // Url to send request to server
        emptyInputText: gettext("placeholder, type to overwrite..."),
        uniqueIdentifier: "id",
        preventBlurOnClick: "",
        onSuccess: function(element, resp){
            return true;
        },
        onError: function(resp){
            showErrorMessages(resp);
        },
        rangeUpdate: function(editable, newVal){
            editable.text(newVal);
        },
        rangePosition: "middle", // position of range input from element "middle", "top" or "bottom"
        delayMarkdownInit: 0, // Add ability to delay the get request for markdown
        debug: false,
        focus: false
    };

}( jQuery ));
