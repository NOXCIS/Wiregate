/**
 * tools.js - Copyright(C) 2021 Donald Zou [https://github.com/donaldzou]
 */

$(".ip_dropdown").on("change",function (){
    $(".modal.show .btn").removeAttr("disabled");
});

$(".conf_dropdown").on("change", function (){
    $(".modal.show .ip_dropdown").html('<option value="none" selected="selected" disabled>Loading...');
    $.ajax({
        url: "/get_ping_ip",
        method: "POST",
        data: "config=" + $(this).children("option:selected").val(),
        success: function (res){
            $(".modal.show .ip_dropdown").html("");
            $(".modal.show .ip_dropdown").append('<option value="none" selected="selected" disabled>Choose an IP');
            $(".modal.show .ip_dropdown").append(res);
        }
    });
});
// Ping Tools
$(".send_ping").on("click", function (){
    $(this).attr("disabled","disabled");
    $(this).html("Pinging...");
    $("#ping_modal .form-control").attr("disabled","disabled");
    $.ajax({
        method:"POST",
        data: "ip="+ $(':selected', $("#ping_modal .ip_dropdown")).val() +
            "&count=" + $("#ping_modal .ping_count").val(),
        url: "/ping_ip",
        success: function (res){
            $(".ping_result tbody").html("");
            let html = '<tr><th scope="row">Address</th><td>'+res.address+'</td></tr>' +
                '<tr><th scope="row">Is Alive</th><td>'+res.is_alive+'</td></tr>' +
                '<tr><th scope="row">Min RTT</th><td>'+res.min_rtt+'ms</td></tr>' +
                '<tr><th scope="row">Average RTT </th><td>'+res.avg_rtt+'ms</td></tr>' +
                '<tr><th scope="row">Max RTT</th><td>'+res.max_rtt+'ms</td></tr>' +
                '<tr><th scope="row">Package Sent</th><td>'+res.package_sent+'</td></tr>' +
                '<tr><th scope="row">Package Received</th><td>'+res.package_received+'</td></tr>' +
                '<tr><th scope="row">Package Loss</th><td>'+res.package_loss+'</td></tr>';
            $(".ping_result tbody").html(html);
            $(".send_ping").removeAttr("disabled");
            $(".send_ping").html("Ping");
            $("#ping_modal .form-control").removeAttr("disabled");
        }
    });
});

// Traceroute Tools
$(".send_traceroute").on("click", function (){
    $(this).attr("disabled","disabled");
    $(this).html("Tracing...");
    $("#traceroute_modal .form-control").attr("disabled","disabled");
    $.ajax({
        url: "/traceroute_ip",
        method: "POST",
        data: "ip=" + $(':selected', $("#traceroute_modal .ip_dropdown")).val(),
        success: function (res){
            $(".traceroute_result tbody").html("");
            res.forEach((ele) =>
                $(".traceroute_result tbody").append('<tr><th scope="row">'+ele.hop+'</th><td>'+ele.ip+'</td><td>'+ele.avg_rtt+'</td><td>'+ele.min_rtt+'</td><td>'+ele.max_rtt+'</td></tr>'));
            $(".send_traceroute").removeAttr("disabled").html("Traceroute");
            $("#traceroute_modal .form-control").removeAttr("disabled");
        }
    });
});
let numberToast = 0;
function showToast(msg, isDanger = false) {
    $(".toastContainer").append(
        `<div id="${numberToast}-toast" class="toast hide animate__animated animate__fadeInUp" role="alert" data-delay="5000">
            <div class="toast-header">
                <strong class="mr-auto">WGDashboard</strong>
                <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="toast-body ${isDanger ? 'text-danger':''}">${msg}</div>
            <div class="toast-progressbar ${isDanger ? 'bg-danger':''}"></div>
        </div>` )
    $(`#${numberToast}-toast`).toast('show');
    $(`#${numberToast}-toast .toast-body`).html(msg);
    $(`#${numberToast}-toast .toast-progressbar`).css("transition", `width ${$(`#${numberToast}-toast .toast-progressbar`).parent().data('delay')}ms cubic-bezier(0, 0, 0, 0)`);
    $(`#${numberToast}-toast .toast-progressbar`).css("width", "0px");
    let i = numberToast;
    setTimeout(function(){
        $(`#${i}-toast`).removeClass("animate__fadeInUp").addClass("animate__fadeOutRight")
    }, 4500)
    numberToast++;
}