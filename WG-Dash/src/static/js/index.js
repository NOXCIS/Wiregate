let emptyInputFeedback = "Can't leave empty";
$('[data-toggle="tooltip"]').tooltip()
let $add_configuration = $("#add_configuration");

let addConfigurationModal = $("#addConfigurationModal");
$(".bottomNavHome").addClass("active");


addConfigurationModal.modal({
    keyboard: false,
    backdrop: 'static',
    show: false
});

addConfigurationModal.on("hidden.bs.modal", function(){
    $("#add_configuration_form").trigger("reset");
    $("#add_configuration_form input").removeClass("is-valid").removeClass("is-invalid");
    $(".addConfigurationAvailableIPs").text("N/A");
});

$(".toggle--switch").on("change", function(){
    $(this).addClass("waiting").attr("disabled", "disabled");
    let id = $(this).data("conf-id");
    let status = $(this).prop("checked");
    let ele = $(this);
    let label = $(this).siblings("label");
    $.ajax({
        url: `/switch/${id}`
    }).done(function(res){
        let dot = $(`div[data-conf-id="${id}"] .dot`);
        if (res.status){
            if (status){
                dot.removeClass("dot-stopped").addClass("dot-running");
                dot.siblings().text("Running");
                showToast(`${id} is running.`);
            }else{
                dot.removeClass("dot-running").addClass("dot-stopped");
                showToast(`${id} is stopped.`);
            }
        }else{
            ele.parents().children(".card-message").html(`<pre class="index-alert">Configuration toggle failed. Please check the following error message:<br><code>${res.message}</code></pre>`)
            showToast(`${id} toggled failed.`, true);
            if (status){
                ele.prop("checked", false)
            }else{
                ele.prop("checked", true)
            }
        }
        ele.removeClass("waiting").removeAttr("disabled");
    })
});

$(".sb-home-url").addClass("active");

$(".card-body").on("click", function(handle){
    if ($(handle.target).attr("class") !== "toggleLabel" && $(handle.target).attr("class") !== "toggle--switch") {
        let c = $(".card");
        for (let i of c){
            if (i != $(this).parent()[0]){
                $(i).css("transition", "ease-in-out 0.3s").css("opacity", "0.5")
            }
        }
        


        window.open($(this).find("a").attr("href"), "_self");
    }
});

function genKeyPair(){
    let keyPair = window.wireguard.generateKeypair(); 
    $("#addConfigurationPrivateKey").val(keyPair.privateKey).data("checked", true);
}

$("#reGeneratePrivateKey").on("click", function() {
    genKeyPair();
});

$("#toggleAddConfiguration").on("click", function(){
    addConfigurationModal.modal('toggle');
    genKeyPair()
}); 

$("#addConfigurationPrivateKey").on("change", function() {
    $privateKey = $(this);
    $privateKeyFeedback = $("#addConfigurationPrivateKeyFeedback");
    if ($privateKey.val().length != 44){
        invalidInput($privateKey, $privateKeyFeedback, "Invalid length");
    }else{
        validInput($privateKey);
    }
});

function ajaxPostJSON(url, data, doneFunc){
    $.ajax({
        url: url,
        method: "POST",
        data: JSON.stringify(data),
        headers: {"Content-Type": "application/json"}
    }).done(function (res) { 
        doneFunc(res);
    });
}

function validInput(input){
    input.removeClass("is-invalid").addClass("is-valid").removeAttr("disabled").data("checked", true);
}
function invalidInput(input, feedback, text){
    input.removeClass("is-valid").addClass("is-invalid").removeAttr("disabled").data("checked", false);
    feedback.addClass("invalid-feedback").text(text);
}

function checkPort($this){
    let port = $this;
    port.attr("disabled", "disabled");
    let portFeedback = $("#addConfigurationListenPortFeedback");
    if (port.val().length == 0){
        invalidInput(port, portFeedback, emptyInputFeedback)
    }else{
        function done(res){
            if(res.status){
                validInput(port);
            }else{
                invalidInput(port, portFeedback, res.reason)
            }
        }
        ajaxPostJSON('/api/addConfigurationPortCheck', {"port": port.val()}, done);
    }
}
$("#addConfigurationListenPort").on("change", function(){
    checkPort($(this));
})

function checkAddress($this){
    let address = $this;
    address.attr("disabled", "disabled");
    let availableIPs = $(".addConfigurationAvailableIPs");
    let addressFeedback = $("#addConfigurationAddressFeedback");
    if (address.val().length == 0){
        invalidInput(address, addressFeedback, emptyInputFeedback);
        availableIPs.html(`N/A`);
    }else{
        function done(res){
            if (res.status){
                availableIPs.html(`<strong>${res.data}</strong>`);
                validInput(address);
            }else{
                invalidInput(address, addressFeedback, res.reason);
                availableIPs.html(`N/A`);
            }
        }
        ajaxPostJSON("/api/addConfigurationAddressCheck", {"address": address.val()}, done)
    }
}
$("#addConfigurationAddress").on("change", function(){
    checkAddress($(this));
});


function checkName($this){
    let name = $this;
    let nameFeedback = $("#addConfigurationNameFeedback");
    name.val(name.val().replace(/\s/g,'')).attr("disabled", "disabled");
    if (name.val().length === 0){
        invalidInput(name, nameFeedback, emptyInputFeedback)
    }else{
        function done(res){
            if (res.status){
                validInput(name);
            }else{
                invalidInput(name, nameFeedback, res.reason);
            }
        }
        ajaxPostJSON("/api/addConfigurationNameCheck", {"name": name.val()}, done);
    }
}
$("#addConfigurationName").on("change", function(){
    checkName($(this));
});





$("#addConfigurationBtn").on("click", function(){
    let btn = $(this);
    let input = $("#add_configuration_form input");
    let filled = true;
    for (let i = 0; i < input.length; i++){
        let $i = $(input[i]);
        if ($i.attr("required") != undefined){
            if ($i.val().length == 0 && $i.attr("name") !== "addConfigurationPrivateKey"){
                invalidInput($i, $i.siblings(".input-feedback"), emptyInputFeedback);
                filled = false;
            }
            if ($i.val().length != 44 && $i.attr("name") == "addConfigurationPrivateKey"){
                invalidInput($i, $i.siblings(".input-feedback"), "Invalid length");
                filled = false;
            }
            if (!$i.data("checked")){
                filled = false;
            }
        }  
    }
    if (filled){
        $("#addConfigurationModal .modal-footer .btn").hide();
        $(".addConfigurationStatus").removeClass("d-none");
        let data = {};
        let q = [];
        for (let i = 0; i < input.length; i++){
            let $i = $(input[i]);
            data[$i.attr("name")] = $i.val();
            q.push($i.attr("name"));
        }
        let done = (res) => {
            let name = res.data;
            $(".addConfigurationAddStatus").removeClass("text-primary").addClass("text-success").html(`<i class="bi bi-check-circle-fill"></i> ${name} added successfully.`);
            if (res.status){
                setTimeout(() => {
                    $(".addConfigurationToggleStatus").removeClass("waiting").html(`<div class="spinner-border spinner-border-sm" role="status"></div> Toggle Configuration`)
                    $.ajax({
                        url: `/switch/${name}`
                    }).done(function(res){
                        if (res.status){
                            $(".addConfigurationToggleStatus").removeClass("text-primary").addClass("text-success").html(`<i class="bi bi-check-circle-fill"></i> Toggle Successfully. Refresh in 5 seconds.`);
                            setTimeout(() => {
                                $(".addConfigurationToggleStatus").text("Refeshing...")
                                location.reload();
                            }, 5000);
                        }else{
                            $(".addConfigurationToggleStatus").removeClass("text-primary").addClass("text-danger").html(`<i class="bi bi-x-circle-fill"></i> ${name} toggle failed.`)
                            $("#addCconfigurationAlertMessage").removeClass("d-none").html(`${name} toggle failed. Please check the following error message:<br>${res.message}`);
                        }
                    });
                }, 500);
            }else{
                $(".addConfigurationStatus").removeClass("text-primary").addClass("text-danger").html(`<i class="bi bi-x-circle-fill"></i> ${name} adding failed.`)
                $("#addCconfigurationAlert").removeClass("d-none").children(".alert-body").text(res.reason);
            }
        };
        ajaxPostJSON("/api/addConfiguration", data, done);
    }
});