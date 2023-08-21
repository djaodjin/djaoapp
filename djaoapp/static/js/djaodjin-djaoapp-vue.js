// specifics to DjaoApp

var AccountTypeAhead = Vue.component('account-typeahead', {
  mixins: [
      typeAheadMixin
  ],
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
      } else if( vm.query ) {
          vm.onHit(vm.query);
      }
    },

    onHit: function onHit(newItem) {
      var vm = this;
      vm.$emit('selectitem', newItem);
      vm.clear();
    }
  }
});


Vue.component('agreement-list', {
    mixins: [
        itemListMixin,
    ],
    data: function() {
        return {
            url: this.$urls.provider.api_agreements,
            newItem: {
                title: '',
                slug: '',
                modified: null,
                ends_at: null
            },
        }
    },
    methods: {
        _asAPIData: function(item) {
            var data = {};
            for( var key in item ) {
                if( item.hasOwnProperty(key) ) {
                    if( key === 'ends_at' ) {
                        data['modified'] = item['ends_at'];
                    } else if( key !== 'modified' ) {
                        data[key] = item[key];
                    }
                }
            }
            return data;
        }
        remove: function(idx){
            var vm = this;
            const slug = vm.items.results[idx].slug;
            vm.reqDelete(vm._safeUrl(vm.url, slug),
            function() {
                vm.get();
            });
        },
        update: function(idx){
            var vm = this;
            const slug = vm.items.results[idx].slug;
            for( var key in vm.items.results[idx] ) {
                if( vm.items.results[idx].hasOwnProperty(key) ) {
                    data[key] = vm.items.results[idx][key];
                }
            }
            vm.reqPatch(vm._safeUrl(vm.url, slug),
                vm._asAPIData(vm.items.results[idx]),
            function() {
                vm.get();
            });
        },
        create: function(){
            var vm = this;
            vm.reqPost(vm.url, vm._asAPIData(vm.newItem),
            function() {
                vm.get();
                vm.newItem = {
                    title: '', slug: '', modified: null, ends_at: null}
            });
        },
    },
    mounted: function(){
        this.get()
    }
});


Vue.component('notification-test', {
    mixins: [
        httpRequestMixin
    ],
    props: ['notificationId'],
    data: function() {
        return {
            url: this.$urls.send_test_email ? this.$urls.send_test_email : null,
        }
    },
    methods: {
        submit: function() {
            var vm = this;
            vm.reqPost(vm._safeUrl(vm.url, vm.notificationId));
        },
    },
});


Vue.component('role-user-list-modal', {
    methods: {
        create: function() {
            var dialog = $("#add-or-create");
            if( dialog.length > 0 ) {
               if( dialog.hasClass('modal') ) {
                   dialog.modal("show");
               } else if( dialog.hasClass('collapse') ) {
                   dialog.collapse("show");
               }
            }
        },
        createCompleted: function() {
            var dialog = $("#add-or-create");
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
    },
    mounted: function() {
        var vm = this;
        jQuery(document).ready(function($) {
            jQuery('#add-or-create').on('shown.bs.collapse', function () {
                vm.$refs.profiles.$refs.typeahead.$refs.input.focus();
            });
        });
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
