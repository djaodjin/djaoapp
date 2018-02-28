/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global jQuery window confirm Plan showMessages:true */

(function ($){
    "use strict";

    function EditPlan(el, options){
        var self = this;
        self.$el = $(el);
        self.options = options;
        self.init();
        return self;
    }

    EditPlan.prototype = {
        init: function(){
            var self = this;
            var editionTool = "<button class=\"text-danger trash-plan close\" style=\"position:absolute;top:50px; left:20px;\"><i class=\"fa fa-trash-o icon_edition\"></i></button> \
                                <button class=\"text-danger edit-plan close\" style=\"position:absolute;top:80px; left:20px;\"><i class=\"fa fa-pencil icon_edition\"></i></button>";

            this.$el.append(editionTool);
            this.$el.on("click", ".trash-plan", function(event){
                self.deletePlan(event);
            });
            this.$el.on("click", ".edit-plan", function(event){
                self.editPlanElement(event);
            });
            this.$el.on("click", self.documentClick);
        },

        deletePlan: function(event){
            var self = this;
            event.preventDefault();
            var plan = new Plan(self.$el.data("slug"),
                {"saas_api_plan": self.options.baseUrl});
            plan.destroy(
                function(){
                    self.$el.remove();
                },
                function(response){
                    if (response.status === 403){
                        showMessages([response.responseJSON.detail], "error");
                    }
                }
            );
        },

        editPlanElement: function(event){
            var self = this;
            event.preventDefault();
            var planSlug = self.$el.data("slug");
            window.location = self.options.baseEditPlanUrl + planSlug + "/";
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
