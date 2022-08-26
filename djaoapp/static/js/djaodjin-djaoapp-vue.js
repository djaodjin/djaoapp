// specifics to DjaoApp

var AccountTypeAhead = Vue.component('account-typeahead', TypeAhead.extend({
  props: ['dataset'],
  data: function data() {
    return {
      url: this.$urls.api_candidates,
     };
  },
  methods: {
    setActiveAndHit: function(item) {
      var vm = this;
      vm.setActive(item);
      vm.hit();
    },

    hit: function() {
      var vm = this;
      if( vm.current !== -1 ) {
        vm.onHit(vm.items[vm.current]);
      } else {
        vm.search();
      }
    },

    onHit: function onHit(newItem) {
      var vm = this;
      vm.$emit('selectitem', newItem);
      vm.reset();
      vm.clear();
    }
  }
}));

var SubscriptionTypeAhead = Vue.component('subscription-typeahead',
    TypeAhead.extend({
}));

Vue.component('role-user-list-modal', {
    methods: {
        create: function() {
            var dialog = $(".create-profile");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("show");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("show");
               }
            }
        },
        createCompleted: function() {
            var dialog = $(".create-profile");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("hide");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("hide");
               }
            }
        },
        remove: function() {
            var dialog = $(".revoke-modal");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("show");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("show");
               }
            }
        },
        removeCompleted: function() {
            var dialog = $(".revoke-modal");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("hide");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("hide");
               }
            }
        }
    }
});


Vue.component('recent-activity', {
    mixins: [
        itemListMixin
    ],
    data: function(){
        return {
            url: this.$urls.recent_activity,
        }
    },
    mounted: function(){
        this.get();
    },
});


Vue.component('todo-list', {
    mixins: [
        itemListMixin
    ],
    data: function(){
        return {
            url: this.$urls.api_todos,
        }
    },
    mounted: function(){
        this.get();
    },
});
