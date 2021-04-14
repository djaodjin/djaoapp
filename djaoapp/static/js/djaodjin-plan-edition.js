/* Copyright (c) 2019, Djaodjin Inc.
   see LICENSE
*/

/* global jQuery window confirm Plan showErrorMessages:true */

(function ($){
    "use strict";

    function EditPlan(el, options){
        var self = this;
        self.element = $(el);
        self.options = options;
        self.init();
        return self;
    }

    EditPlan.prototype = {
        init: function(){
            var self = this;
            var editionTool = "<button class=\"edit-plan close\" style=\"position:absolute;top:30px; left:20px;\"><i class=\"fa fa-pencil icon_edition\"></i></button><button class=\"text-danger trash-plan close\" style=\"position:absolute;top:30px; right:20px;\"><i class=\"fa fa-trash-o icon_edition\"></i></button>";

            this.element.append(editionTool);
            this.element.on("click", ".trash-plan", function(event){
                self.deletePlan(event);
            });
            this.element.on("click", ".edit-plan", function(event){
                self.editPlanElement(event);
            });
            this.element.on("click", self.documentClick);
        },

        _getCSRFToken: function() {
            var self = this;
            var crsfNode = self.element.find("[name='csrfmiddlewaretoken']");
            if( crsfNode.length > 0 ) {
                return crsfNode.val();
            }
            return getMetaCSRFToken();
        },

        deletePlan: function(event){
            var self = this;
            event.preventDefault();
            // XXX following is matching statement in djaodjin-saas.js
            // We do this here because the slug might have been updated.
            self.id = self.element.attr("data-plan");
            $.ajax({ type: "DELETE",
                 url: self.options.baseUrl + "/" + self.id + "/",
                 beforeSend: function(xhr) {
                     xhr.setRequestHeader("X-CSRFToken", self._getCSRFToken());
                 },
                 async: false,
                 success: function(data) {
                     // XXX We cannot just do a `self.element.remove();`
                     // otherwise the layout is incorrect.
                     location.reload(true);
                 },
                 error: function(resp) {
                     showErrorMessages(resp);
                 }
            });
        },

        editPlanElement: function(event){
            var self = this;
            event.preventDefault();
            // XXX following is matching statement in djaodjin-saas.js
            // We do this here because the slug might have been updated.
            self.id = self.element.attr("data-plan");
            window.location = self.options.baseEditPlanUrl + self.id + "/";
        }

    };

    $.fn.editPlan = function(options) {
        var opts = $.extend( {}, $.fn.editPlan.defaults, options );
        return this.each(function() {
            var editplan = new EditPlan($(this), opts);
        });
    };

    $.fn.editPlan.defaults = {
        baseUrl: null,
        baseEditPlanUrl: null
    };
})(jQuery);
