// **************************************************
// PROVISION/SELLER PAGE DECLARATION: ext/seller.html
// --------------------------------------------------
// Version: 1.00
// Date: 30-11-2019

default_submit_mode = 2;

// Caption scrool state
var caption_state = 0;

// Caption params
var caption_top = 0;
var caption_height = 0;

// Animate timeout
var animate_timeout = 300;
var timer = null;

// ----------------------
// Dialog Action Handlers
// ----------------------

function $animate() {
    if (caption_state == -1) {
        clearTimeout(timer);
        timer = null;

        $("#caption").removeClass('hidden').css({ top: -caption_height, transform: 'translateY(100%)' });

        caption_state = 1;
    }
}

function $freeze() {
    if (caption_state == -1) {
        clearTimeout(timer);
        timer = null;

        $("#caption").removeClass('fixed').css({ top:0, transform: 'none' });
        
        caption_state = 0;
    }

    $("#line-content").css({ marginTop: 0 });
}

// --------------
// Page Functions
// --------------

IsTrace = 0;

function $Init() {
}

// =========================
// Custom routine assigments
// =========================


// ====================
// Page Event Listeners
// ====================

jQuery(function($) 
{
    // ---------------
    // Register's Form
    // ---------------

    $("#caption").one("webkitTransitionEnd otransitionend oTransitionEnd msTransitionEnd transitionend", function() {
        //alert(1);
    });

    // -------------
    // Resize window
    // -------------

    $(window).scroll(function(e) {
        var scrool = $(window).scrollTop();

        //alert(caption_state);

        if (scrool > caption_top + caption_height) {
            if (caption_state == 0) {
                $("#line-content").css({ marginTop: caption_height+10 });
                $("#caption").addClass('hidden').addClass('fixed');
                timer = setTimeout($animate, animate_timeout);
                caption_state = -1;
            }
        } else if (scrool == 0) {
            if (caption_state == 1) {
                timer = setTimeout($freeze, animate_timeout);
                caption_state = -1;
            }
        }
    });

    // --------
    // Keyboard
    // --------

    $(window).keydown(function(e) {
        if ($ConfirmDialog.is_focused() || $NotificaptionDialog.is_focused())
            return;

        if (is_show_error)
            return;

        if (e.keyCode==13) {                                     // Enter
        }

        if (is_search_focused)
            return;

        var exit = false;

        //alert(e.ctrlKey+':'+e.shiftKey+':'+e.altKey+':'+e.keyCode);

        if (exit) {
            e.preventDefault();
            return false;
        }
    });
});

function page_is_focused(e) {
    return false;
}

function resize() {
}

// =======
// STARTER
// =======

$(function() 
{
    if (IsTrace)
        alert('Document Ready (seller)');

    current_context = 'seller';
    resize();

    var ob = $("#caption");
    
    caption_top = ob.position().top;
    caption_height = ob.height() + 25; // padding+border

    //alert(caption_height);

    ob.css({ width: $_get_css_size($("#line-content").width()) });

    try {
        $_init();
    }
    catch(e) {}
});
