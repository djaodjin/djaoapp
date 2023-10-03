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

var AddressTypeAhead = Vue.component('address-typeahead', {
  mixins: [
    typeAheadMixin,
    httpRequestMixin
  ],
  data: function data() {
    return {
      url: this.$urls.api_places_suggestions,
      query: '',
     };
  },
  mounted: function() {
    var container = $(this.$el).parent()
    this.query = container.find('input[name="street_address"]').attr('data-value')
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

    lookupPlace: function(placeId) {
      var vm = this;
      return new Promise(function(resolve, reject) {
        vm.reqGet(vm._safeUrl(vm.url, placeId), resolve, reject);
      });
    },

    updateForm: function(place) {
      var vm = this;
      var container = $(vm.$el).parent()
      var countryCnt = container.find('select[name="country"] option')

      if (place.locality || place.sublocality) {
        var locality = place.locality ? place.locality : place.sublocality;
        container.find('input[name="locality"]').val(locality);
      }
      if (place.postal_code) {
        container.find('input[name="postal_code"]').val(place.postal_code);
      }
      if (place.country) {
        countryCnt.filter('[value="' + place.country_code + '"]').prop('selected', 'selected').trigger('change');
      }
      if (place.state) {
        if (place.country_code === 'US' || place.country_code === 'CA') {
          var stateCnt = container.find('select[name="region"] option')
          stateCnt.filter('[value="' + place.state_code + '"]').prop('selected', 'selected');
        } else {
          container.find('input[name="region"]').val(place.state_code);
        }
      }

      var address = '';
      if( place.street_number ) {
        address += place.street_number + ' ';
      }
      if (place.route) {
        address += place.route;
      }
      vm.query = address;
      container.find('input[name="street_address"]').val(address);
    },

    onHit: function onHit(newItem) {
      var vm = this;
      vm.lookupPlace(newItem.place_id).then(function(place) {
        vm.updateForm(place);
        vm.clear();
      });
    },
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
        },
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

Vue.directive('init-croppa', {
inserted: function(el) {
    var croppaInstance = el.__vue__;

    if (croppaInstance && typeof croppaInstance.addClipPlugin === 'function') {
        croppaInstance.addClipPlugin(function(ctx, x, y, w, h) {
          ctx.beginPath();
          ctx.arc(x + w / 2, y + h / 2, w / 2, 0, 2 * Math.PI, true);
          ctx.closePath();
        });
      }
    }
});

Vue.directive('zoom-slider', {
    inserted: function (el) {
        var croppaInstance = el.__vue__;
        el.style.position = 'relative';
        var slider = document.createElement('input');
        slider.className = 'imageSlider';

        slider.type = 'range';
        slider.min = '2';
        slider.max = '10';
        slider.step = '0.001';
        slider.value = '2';
        slider.style.display = 'block';
        el.appendChild(slider);

        slider.addEventListener('input', function(evt) {
            croppaInstance.scaleRatio = parseFloat(evt.target.value);
        });
    }
});
