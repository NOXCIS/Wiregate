import{_ as R,D as k,g as b,c as l,b as e,d,m as u,y as _,F as c,h as p,e as m,s as I,t as i,w as f,T as v,a as n,f as g,n as h,z as P,i as w,j as x}from"./index-glbWjskj.js";import{L as C}from"./localeText-CS3fF34S.js";import{O as A}from"./osmap-BjMGYJcF.js";const S={name:"ping",components:{OSMap:A,LocaleText:C},data(){return{loading:!1,cips:{},selectedConfiguration:void 0,selectedPeer:void 0,selectedIp:void 0,count:4,pingResult:void 0,pinging:!1}},setup(){return{store:k()}},mounted(){b("/api/ping/getAllPeersIpAddress",{},a=>{a.status&&(this.loading=!0,this.cips=a.data,console.log(this.cips))})},methods:{execute(){this.selectedIp&&(this.pinging=!0,this.pingResult=void 0,b("/api/ping/execute",{ipAddress:this.selectedIp,count:this.count},a=>{a.status?this.pingResult=a.data:this.store.newMessage("Server",a.message,"danger"),this.pinging=!1}))}},watch:{selectedConfiguration(){this.selectedPeer=void 0,this.selectedIp=void 0},selectedPeer(){this.selectedIp=void 0}}},T={class:"mt-md-5 mt-3 text-body"},M={class:"container"},V={class:"row"},$={class:"col-sm-4 d-flex gap-2 flex-column"},L={class:"mb-1 text-muted",for:"configuration"},N=["disabled"],O=["value"],B={class:"mb-1 text-muted",for:"peer"},D=["disabled"],U=["value"],z={class:"mb-1 text-muted",for:"ip"},E=["disabled"],F={class:"d-flex align-items-center gap-2"},G={class:"text-muted"},j={class:"mb-1 text-muted",for:"ipAddress"},H=["disabled"],Y={class:"mb-1 text-muted",for:"count"},q={class:"d-flex gap-3 align-items-center"},J=["disabled"],K=["disabled"],Q={key:0,class:"d-block"},W={key:1,class:"d-block"},X={class:"col-sm-8 position-relative"},Z={key:"pingPlaceholder"},ee={key:"pingResult",class:"d-flex flex-column gap-2 w-100"},se={class:"card rounded-3 bg-transparent shadow-sm animate__animated animate__fadeIn",style:{"animation-delay":"0.15s"}},te={class:"card-body row"},ie={class:"col-sm"},ne={class:"mb-0 text-muted"},le={key:0,class:"col-sm"},de={class:"mb-0 text-muted"},oe={class:"card rounded-3 bg-transparent shadow-sm animate__animated animate__fadeIn",style:{"animation-delay":"0.3s"}},ae={class:"card-body"},re={class:"card rounded-3 bg-transparent shadow-sm animate__animated animate__fadeIn",style:{"animation-delay":"0.45s"}},ue={class:"card-body"},ce={class:"mb-0 text-muted"},pe={class:"card rounded-3 bg-transparent shadow-sm animate__animated animate__fadeIn",style:{"animation-delay":"0.6s"}},me={class:"card-body"},ge={class:"mb-0 text-muted"};function _e(a,s,he,be,fe,ve){const o=x("LocaleText"),y=x("OSMap");return n(),l("div",T,[e("div",M,[s[19]||(s[19]=e("h3",{class:"mb-3 text-body"},"Ping",-1)),e("div",V,[e("div",$,[e("div",null,[e("label",L,[e("small",null,[d(o,{t:"Configuration"})])]),u(e("select",{class:"form-select","onUpdate:modelValue":s[0]||(s[0]=t=>this.selectedConfiguration=t),disabled:this.pinging},[s[7]||(s[7]=e("option",{disabled:"",selected:"",value:void 0},null,-1)),(n(!0),l(c,null,p(this.cips,(t,r)=>(n(),l("option",{value:r},i(r),9,O))),256))],8,N),[[_,this.selectedConfiguration]])]),e("div",null,[e("label",B,[e("small",null,[d(o,{t:"Peer"})])]),u(e("select",{id:"peer",class:"form-select","onUpdate:modelValue":s[1]||(s[1]=t=>this.selectedPeer=t),disabled:this.selectedConfiguration===void 0||this.pinging},[s[8]||(s[8]=e("option",{disabled:"",selected:"",value:void 0},null,-1)),this.selectedConfiguration!==void 0?(n(!0),l(c,{key:0},p(this.cips[this.selectedConfiguration],(t,r)=>(n(),l("option",{value:r},i(r),9,U))),256)):m("",!0)],8,D),[[_,this.selectedPeer]])]),e("div",null,[e("label",z,[e("small",null,[d(o,{t:"IP Address"})])]),u(e("select",{id:"ip",class:"form-select","onUpdate:modelValue":s[2]||(s[2]=t=>this.selectedIp=t),disabled:this.selectedPeer===void 0||this.pinging},[s[9]||(s[9]=e("option",{disabled:"",selected:"",value:void 0},null,-1)),this.selectedPeer!==void 0?(n(!0),l(c,{key:0},p(this.cips[this.selectedConfiguration][this.selectedPeer].allowed_ips,t=>(n(),l("option",null,i(t),1))),256)):m("",!0)],8,E),[[_,this.selectedIp]])]),e("div",F,[s[10]||(s[10]=e("div",{class:"flex-grow-1 border-top"},null,-1)),e("small",G,[d(o,{t:"OR"})]),s[11]||(s[11]=e("div",{class:"flex-grow-1 border-top"},null,-1))]),e("div",null,[e("label",j,[e("small",null,[d(o,{t:"Enter IP Address / Hostname"})])]),u(e("input",{class:"form-control",type:"text",id:"ipAddress",disabled:this.pinging,"onUpdate:modelValue":s[3]||(s[3]=t=>this.selectedIp=t)},null,8,H),[[I,this.selectedIp]])]),s[16]||(s[16]=e("div",{class:"w-100 border-top my-2"},null,-1)),e("div",null,[e("label",Y,[e("small",null,[d(o,{t:"Count"})])]),e("div",q,[e("button",{onClick:s[4]||(s[4]=t=>this.count--),disabled:this.count===1,class:"btn btn-sm bg-secondary-subtle text-secondary-emphasis"},s[12]||(s[12]=[e("i",{class:"bi bi-dash-lg"},null,-1)]),8,J),e("strong",null,i(this.count),1),e("button",{role:"button",onClick:s[5]||(s[5]=t=>this.count++),class:"btn btn-sm bg-secondary-subtle text-secondary-emphasis"},s[13]||(s[13]=[e("i",{class:"bi bi-plus-lg"},null,-1)]))])]),e("button",{class:"btn btn-primary rounded-3 mt-3 position-relative",disabled:!this.selectedIp||this.pinging,onClick:s[6]||(s[6]=t=>this.execute())},[d(v,{name:"slide"},{default:f(()=>[this.pinging?(n(),l("span",W,s[15]||(s[15]=[e("span",{class:"spinner-border spinner-border-sm","aria-hidden":"true"},null,-1),e("span",{class:"visually-hidden",role:"status"},"Loading...",-1)]))):(n(),l("span",Q,s[14]||(s[14]=[e("i",{class:"bi bi-person-walking me-2"},null,-1),g("Ping! ")])))]),_:1})],8,K)]),e("div",X,[d(v,{name:"ping"},{default:f(()=>[this.pingResult?(n(),l("div",ee,[this.pingResult.geo&&this.pingResult.geo.status==="success"?(n(),w(y,{key:0,d:this.pingResult},null,8,["d"])):m("",!0),e("div",se,[e("div",te,[e("div",ie,[e("p",ne,[e("small",null,[d(o,{t:"IP Address"})])]),g(" "+i(this.pingResult.address),1)]),this.pingResult.geo&&this.pingResult.geo.status==="success"?(n(),l("div",le,[e("p",de,[e("small",null,[d(o,{t:"Geolocation"})])]),g(" "+i(this.pingResult.geo.city)+", "+i(this.pingResult.geo.country),1)])):m("",!0)])]),e("div",oe,[e("div",ae,[s[18]||(s[18]=e("p",{class:"mb-0 text-muted"},[e("small",null,"Is Alive")],-1)),e("span",{class:h([this.pingResult.is_alive?"text-success":"text-danger"])},[e("i",{class:h(["bi me-1",[this.pingResult.is_alive?"bi-check-circle-fill":"bi-x-circle-fill"]])},null,2),g(" "+i(this.pingResult.is_alive?"Yes":"No"),1)],2)])]),e("div",re,[e("div",ue,[e("p",ce,[e("small",null,[d(o,{t:"Average / Min / Max Round Trip Time"})])]),e("samp",null,i(this.pingResult.avg_rtt)+"ms / "+i(this.pingResult.min_rtt)+"ms / "+i(this.pingResult.max_rtt)+"ms ",1)])]),e("div",pe,[e("div",me,[e("p",ge,[e("small",null,[d(o,{t:"Sent / Received / Lost Package"})])]),e("samp",null,i(this.pingResult.package_sent)+" / "+i(this.pingResult.package_received)+" / "+i(this.pingResult.package_loss),1)])])])):(n(),l("div",Z,[s[17]||(s[17]=e("div",{class:"pingPlaceholder bg-body-secondary rounded-3 mb-3",style:{height:"300px"}},null,-1)),(n(),l(c,null,p(4,t=>e("div",{class:h(["pingPlaceholder bg-body-secondary rounded-3 mb-3",{"animate__animated animate__flash animate__slower animate__infinite":this.pinging}]),style:P({"animation-delay":`${t*.15}s`})},null,6)),64))]))]),_:1})])])])])}const ke=R(S,[["render",_e],["__scopeId","data-v-a08ce97e"]]);export{ke as default};
