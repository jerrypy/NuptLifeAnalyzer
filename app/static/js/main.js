$(function() {
    "use strict";
    $(".title").sparkle({
		fill:"#eee"	,
		stroke:"#eee",
		size: 20,
	  }).sparkle({
		delay: 1000,
		pause: 750,
		size: 10
	  });

    $('#modal1').modal('hide');
    $('#privacy').click(function () {
        $('#modal1').modal('show');
    });


    var youjiData = Object();
    var lib_crawler_start = false;
    var ehome_crawler_start = false;

    var clickEvent = (document.ontouchstart!==null) ? 'click' : 'touchstart';
    
    var sliderOpts = {
        wrap: '.wrapper',
        item: '.page',
        lastLocate: false,

        // slider需加载的资源
        loadingImgs: [
            'http://static.jerrywin.com/youji/img/army.png',
            'http://static.jerrywin.com/youji/img/balloon.png',
            'http://static.jerrywin.com/youji/img/blackboard.png',
            'http://static.jerrywin.com/youji/img/book.png',
            'http://static.jerrywin.com/youji/img/cash.png',
            'http://static.jerrywin.com/youji/img/classroom.png',
            'http://static.jerrywin.com/youji/img/cloud.png',
            'http://static.jerrywin.com/youji/img/coin.png',
            'http://static.jerrywin.com/youji/img/desk.png',
            'http://static.jerrywin.com/youji/img/gate.png',
            'http://static.jerrywin.com/youji/img/girl.png',
            'http://static.jerrywin.com/youji/img/graduates.png',
            'http://static.jerrywin.com/youji/img/guy.png',
            'http://static.jerrywin.com/youji/img/library.png',
            'http://static.jerrywin.com/youji/img/man.png',
            'http://static.jerrywin.com/youji/img/no1.png',
            'http://static.jerrywin.com/youji/img/paper_left.png',
            'http://static.jerrywin.com/youji/img/paper_right.png',
            'http://static.jerrywin.com/youji/img/rain.png',
            'http://static.jerrywin.com/youji/img/rainbow.png',
            'http://static.jerrywin.com/youji/img/sandclock.png',
            'http://static.jerrywin.com/youji/img/selfie_man.png',
            'http://static.jerrywin.com/youji/img/selfie_woman.png',
            'http://static.jerrywin.com/youji/img/stage.png',
            'http://static.jerrywin.com/youji/img/students.png',
            'http://static.jerrywin.com/youji/img/sun.png',
            'http://static.jerrywin.com/youji/img/wallet.png',

        ],
        
        onloading: function (loaded, total) {
             $('#loading_text span').text(loaded/total*100+'%');
            if (loaded==total) {
                $('#loading_text').css('display', 'none');
            }
        }
    };
    var animationEvent = whichAnimationEvent();
    function whichAnimationEvent(){
        //检测浏览器内核类型
        var t,
            el = document.createElement("fakeelement");

        var animations = {
            "animation"      : "animationend",
            "OAnimation"     : "oAnimationEnd",
            "MozAnimation"   : "animationend",
            "WebkitAnimation": "webkitAnimationEnd"
        };

        for (t in animations){
            if (el.style[t] !== undefined){
                return animations[t];
            }
        }
    }

    // 登录页面需加载的资源
    var preload = [
        'http://static.jerrywin.com/youji/img/arrow.png',
        'http://static.jerrywin.com/youji/img/phone.png',
        'http://static.jerrywin.com/youji/img/star_web.jpg',
        'http://static.jerrywin.com/youji/img/mask.png',
        'http://static.jerrywin.com/youji/img/sound.png',
        'http://static.jerrywin.com/youji/img/sound_muted.png',
        'http://static.jerrywin.com/youji/music/nupt_mid.mp3'
    ];

    new preloader({
        files: preload,
        progress: function (err, response, percent) {
            $('.percent span').text(percent + '%');
        },
        complete: function () {
            $('#wrapper').show();
            $('.preloader').addClass('loaded');
            $('.preloader').remove();
            bgAudio.play();
        }
    });
    
    
    $('#zf_login').click(function () {
        if ($('#student_id').val() === "" || $('#password').val() === ""){
            swal({
                    title: '请填写完整。',
                    type: 'error',
                    allowOutsideClick: true,
                    showConfirmButton: false,
                    timer: 2000
                });
            return false;
        }
       $('.loginWrapper').hide();
        $('.loader').show();
        $.ajax({
          type: 'POST',
          url: '/get_zf_data_decaptcha',
          data: $('#zf_form').serialize(),
          success: function(data, status, request){
              var status_url = request.getResponseHeader('Location');
              update_data(status_url);
          },
          error: function(data, status, request){
              $('.loader').hide();
                $('#loading_text').hide();
                $('.loginWrapper').show();
                swal({
                    title: '服务器异常，请重试。',
                    type: 'error',
                    allowOutsideClick: true,
                    showConfirmButton: false,
                    timer: 2000
                })
          }
        });
    });

    function update_data(status_url) {
        $.getJSON(status_url, function (data) {
            if (data['state'] == 'FAILURE') {
                $('.loader').hide();
                $('#loading_text').hide();
                $('.loginWrapper').show();
                swal({
                    title: '服务器异常，请重试。',
                    type: 'error',
                    allowOutsideClick: true,
                    showConfirmButton: false,
                    timer: 2000
                })
            }
            else if(data['state'] != 'PENDING' && data['state'] != 'LOGIN_SUCCESS'){
                if ('code' in data){
                    $('.loader').hide();
                    $('#loading_text').hide();
                    $('.loginWrapper').show();
                    if (data['code'] == 5) {
                        swal({
                            title: '正方系统异常，请重试。',
                            type: 'error',
                            allowOutsideClick: true,
                            showConfirmButton: false,
                            timer: 2000
                        })
                    }
                    else {
                        swal({
                            title: '登录失败，请重试。',
                            type: 'error',
                            allowOutsideClick: true,
                            showConfirmButton: false,
                            timer: 2000
                        })
                    }
                }
                else if('data' in data){
                    youjiData.zf_data = data['data'];
                    youjiData.zf_data['info'] = data['zf_info'];
                    if ('lib_data' in youjiData) {
                        render_data();
                    }
                    if (!lib_crawler_start) {
                        // 有可能worker工作很快直接到success状态，开始Lib爬虫
                        lib_crawler_start = true;
                        get_lib_data();

                    }
                    // get_ehome_data();
                }
                else{
                    // info got
                    youjiData.zf_info = data['zf_info'];
                    lib_crawler_start = true;
                    get_lib_data();

                    setTimeout(function () {
                        update_data(status_url);
                    }, 2000);
                }
            }
            else {
                setTimeout(function () {
                    update_data(status_url);
                }, 2000);
            }
        })
    }

    /**
     * 非南邮用户使用
     */
    $('#try').click(function() {
        "use strict";
        $('.loginWrapper').hide();
        $('.loader').show();
        $('#loading_text').show();
        $.ajax({
            type: 'POST',
            url: '/try',
            data: null,
            success: function (data, status, request) {
                var status_url = request.getResponseHeader('Location');
                update_try_data(status_url);
            },
            error: function (data, status, request) {
                $('.loader').hide();
                $('#loading_text').hide();
                $('.loginWrapper').show();
                swal({
                    title: '服务器异常，请重试。',
                    type: 'error',
                    allowOutsideClick: true,
                    showConfirmButton: false,
                    timer: 2000
                })
            }
        })
    });


    function update_try_data(status_url) {
        $.getJSON(status_url, function (data) {
            var task_state = data['state'];
            if (task_state == 'FAILURE') {
                // task fail
                $('.loader').hide();
                $('#loading_text').hide();
                $('.loginWrapper').show();
                swal({
                        title: '服务器异常，请重试。',
                        type: 'error',
                        allowOutsideClick: true,
                        showConfirmButton: false,
                        timer: 2000
                    })
            }
            else if (task_state != 'PENDING') {
                youjiData['zf_data'] = data['zf_data'];
                youjiData['lib_data'] = data['lib_data'];
                render_data();
                }
            else {
                setTimeout(function(){
                    update_try_data(status_url);
                    }, 1500);
                }
        })
    }

    function get_lib_data(password) {
        $.ajax({
            type: 'POST',
            url: '/get_lib_data',
            data: {'password': password},
            success: function (data, status, request) {
                var status_url = request.getResponseHeader('Location');
                update_lib_data(status_url);
            },
            error: function (data, status, request) {
                $('.loader').hide();
                $('#loading_text').hide();
                $('.loginWrapper').show();
                swal({
                    title: '服务器异常，请重试。',
                    type: 'error',
                    allowOutsideClick: true,
                    showConfirmButton: false,
                    timer: 2000
                })
            }
        })
    }

    function update_lib_data(status_url) {
        $.getJSON(status_url, function (data) {
            var task_state = data['state'];
            if (task_state == 'FAILURE') {
                // task fail
                $('.loader').hide();
                $('#loading_text').hide();
                $('.loginWrapper').show();
                swal({
                        title: '服务器异常，请重试。',
                        type: 'error',
                        allowOutsideClick: true,
                        showConfirmButton: false,
                        timer: 2000
                    })
            }
            else if (task_state != 'PENDING') {
                if ('code' in data) {
                    if (data['code'] == 3) {
                        // 图书馆密码错误
                        swal({
                            title: "",
                            text: "检测你更改过图书馆密码，请输入：",
                            type: "input",
                            showCancelButton: true,
                            closeOnConfirm: false,
                            animation: "slide-from-top",
                            inputPlaceholder: "图书馆密码"
                        }, function (inputValue) {
                            if (inputValue === false) {
                                 $('.loader').hide();
                                $('#loading_text').hide();
                                $('.loginWrapper').show();
                                return false;
                            }
                            else if (inputValue === "") {
                                swal.showInputError("密码不能为空！");
                                return false;
                            }
                            else {
                                swal.close();
                                get_lib_data(inputValue);
                                return false;
                            }
                        });
                    }
                    else {
                        $('.loader').hide();
                        $('#loading_text').hide();
                        $('.loginWrapper').show();
                        swal({
                                title: '服务器异常，请重试。',
                                type: 'error',
                                allowOutsideClick: true,
                                showConfirmButton: false,
                                timer: 2000
                            })
                        }
                    }
                else {
                    youjiData.lib_data = data['data'];
                    if ('zf_data' in youjiData) {
                        // 正方爬取完毕
                        render_data();
                    }
                }
            }
            else {
                setTimeout(function(){
                    update_lib_data(status_url);
                    }, 1500);
                }
        })
    }

    function render_data() {
        youjiData.zf_info = youjiData['zf_data']['info'];
        var entrance_date = new moment(youjiData.zf_info['entrance_date']);
        var today = new moment();
        var delta = moment.duration(today.diff(entrance_date)).asDays();
        youjiData.delta = Math.floor(delta);

        youjiData.weather = youjiData['zf_data']['weather'];
        youjiData.first_borrow_date = new moment(youjiData['lib_data']['analysis']['first_borrow_book'][3]).format('YYYY年M月D日');
        youjiData.first_course_score= youjiData['zf_data']['analysis']['first_course_score'];

        youjiData.fc = !isNaN(parseInt(youjiData.first_course_score));
        youjiData.first_comment_time = new moment(youjiData['lib_data']['analysis']['first_comment'][5]).format('YYYY年MM月DD日 HH时mm分ss秒');

        var tempFn = doT.template(jQuery('#tmpl').html());
        jQuery('#wrapper').html(tempFn(youjiData));

        window.mySlider = new iSlider(sliderOpts);


        
    }

    // 背景音乐控制
    var clickEvent = (document.ontouchstart!==null) ? 'click' : 'touchstart';
    var bgMusic = $('#bgMusic');
    var bgMusicContr = $('#bgMusicContr');
    var bgAudio = document.getElementById("bgMusic");
bgAudio.play();
    $(document).on(clickEvent, '#bgMusicContr', function(e) {
        var $this = $(this);
        if (!$this.hasClass('playing')) {
            document.getElementById("bgMusic").play();
        } else {
            document.getElementById("bgMusic").pause();
        }
    });

    // 播放事件
    bgMusic.on('play', function() {
        bgMusicContr.addClass('playing');
    });

    // 暂停事件
    bgMusic.on('pause', function() {
        bgMusicContr.removeClass('playing');
    });

    // 对不支持自动播放的设备使用一次性的 touchstart 事件触发
    $(document).one('touchstart', function() {
        bgAudio.play();
    });
})