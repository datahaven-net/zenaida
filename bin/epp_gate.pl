#!/usr/bin/perl


use strict;
use warnings;

$|++;

use AnyEvent;
use Net::RabbitFoot;

use TryCatch;

use base qw(Net::Server::PreFork);

# no warnings;

use File::Basename;
use lib dirname (__FILE__);

use Digest::MD5 qw(md5_hex);
use Time::HiRes qw(time);
use Time::Piece;

use JSON;

use Data::Dumper;

use Net::EPP::Simple;
use Net::EPP::Client;
use Net::EPP::Frame;
use Net::EPP::Frame::ObjectSpec;
use Net::EPP::Frame::Command::Create::Domain;

use HTTP::Daemon;
use HTTP::Status;
use HTTP::Request;
use HTTP::Response;


STDERR->autoflush(1);
STDOUT->autoflush(1);


my $epp;
my $conn;
my $channel;


sub lll {
    my $message      = shift;
    my $time = localtime->cdate;
    print "$time: $message" , "\n";
    return 1;
}


sub make_client {
    my $epp_credentials_file = $ARGV[0];
    open (my $inFile, '<', $epp_credentials_file) or die "$epp_credentials_file";
    my $firstLine = <$inFile>;
    close $inFile;
    my ($epp_host, $epp_port, $epp_username, $epp_password) = split / /, $firstLine;
    $epp_host =~ s/^\s+|\s+$//g;
    $epp_port =~ s/^\s+|\s+$//g;

    $epp = Net::EPP::Client->new(
        host    => $epp_host,
        port    => $epp_port,
        ssl     => 1,
        frames  => 1,
    );
    lll("EPP Client started, target host is " . $epp_host . ":" . $epp_port);
    my $greeting = $epp->connect;
    lll('GREETING Response: ' . Dumper($greeting->toString(2)));
    return $epp;
}


sub make_clTRID {
    return md5_hex(Time::HiRes::time().$$);
}


sub hello {
    my $hello = Net::EPP::Frame::Hello->new;
    lll('HELLO Request: ' . Dumper($hello->toString(2)));
    my $hello_response = $epp->request($hello);
    lll('HELLO Response: ' . Dumper($hello_response->toString(2)));
    return 1;
}


sub login {
    my $epp_credentials_file = $ARGV[0];
    open (my $inFile, '<', $epp_credentials_file) or die "$epp_credentials_file";
    my $firstLine = <$inFile>;
    close $inFile;
    my ($epp_host, $epp_port, $epp_username, $epp_password) = split / /, $firstLine;
    $epp_username =~ s/^\s+|\s+$//g;
    $epp_password =~ s/^\s+|\s+$//g;

    my $login = Net::EPP::Frame::Command::Login->new;
    $login->clTRID->appendText(make_clTRID());
    $login->clID->appendText($epp_username);
    $login->pw->appendText($epp_password);
    my $svcExtensionTag = $login->createElement('svcExtension');
    my $idn = $login->createElement('extURI');
    $idn->appendText('urn:ietf:params:xml:ns:idn-1.0');
    $svcExtensionTag->appendChild($idn);
    $login->svcs->appendChild($svcExtensionTag);

    lll('LOGIN Request: ' . Dumper($login->toString(2)));
    my $login_response = $epp->request($login);
    lll('LOGIN Response: ' . Dumper($login_response->toString(2)));

    my $result = ($login_response->getElementsByTagName('result'))[0];
    if ($result->getAttribute('code') != 1000) {
        die("LOGIN failed! : " . $result);
    }
    lll('Logged in with username: ' . $epp_username);
    return 1;
}


sub cmd_poll_req {
    my $args = shift;
    my $req = Net::EPP::Frame::Command::Poll::Req->new;
    $req->clTRID->appendText(make_clTRID());
    return $req;
}


sub cmd_poll_ack {
    my $args = shift;
    my $ack = Net::EPP::Frame::Command::Poll::Ack->new;
    $ack->clTRID->appendText(make_clTRID());
    $ack->setMsgID($args->{msg_id});
    return $ack;
}


sub cmd_domain_check {
    my $args = shift;
    my $check = Net::EPP::Frame::Command::Check::Domain->new;
    $check->clTRID->appendText(make_clTRID());
    foreach my $domain (@{$args->{domains}}){
        $check->addDomain($domain);
    }
    return $check;
}


sub cmd_domain_info {
    my $args = shift;
    my $info = Net::EPP::Frame::Command::Info::Domain->new;
    $info->clTRID->appendText(make_clTRID());
    $info->setDomain($args->{name});
    if (exists $args->{auth_info}) {
        my $authInfo = $info->createElement('domain:authInfo');
        my $pw = $info->createElement('domain:pw');
        $pw->appendText($args->{auth_info});
        $authInfo->appendChild($pw);
        $info->getNode('info')->getChildNodes->shift->appendChild($authInfo);
    }
    return $info;
}


sub cmd_domain_create {
    my $args = shift;
    my $create = Net::EPP::Frame::Command::Create::Domain->new;
    $create->clTRID->appendText(make_clTRID());
    $create->setDomain($args->{name});
    if (exists $args->{auth_info}) {
        $create->setAuthInfo($args->{auth_info});
    }
    if (exists $args->{registrant}) {
        $create->setRegistrant($args->{registrant});
    }
    foreach my $ns (@{$args->{nameservers}}) {
        $create->setNS($ns);
    }
    if (exists $args->{period}) {
        if (exists $args->{period_units}) {
            $create->setPeriod($args->{period}, $args->{period_units});
        } else {
            $create->setPeriod($args->{period});
        }
    }
    $create->setContacts($args->{contacts});
    return $create;
}


sub cmd_domain_update {
    my $args = shift;
    my $update = Net::EPP::Frame::Command::Update::Domain->new;
    $update->clTRID->appendText(make_clTRID());
    $update->setDomain($args->{name});
    foreach my $add_ns (@{$args->{add_nameservers}}) {
        $update->addNS($add_ns);
    }
    foreach my $rem_ns (@{$args->{remove_nameservers}}) {
        $update->remNS($rem_ns);
    }
    foreach my $add_contact (@{$args->{add_contacts}}) {
        $update->addContact($add_contact->{type}, $add_contact->{id});
    }
    foreach my $rem_contact (@{$args->{remove_contacts}}) {
        $update->remContact($rem_contact->{type}, $rem_contact->{id});
    }
    if (exists $args->{change_registrant}) {
        $update->chgRegistrant($args->{change_registrant});
    }
    if (exists $args->{auth_info}) {
        $update->chgAuthInfo($args->{auth_info});
    }
    if (exists $args->{rgp_restore}) {
        my $RGP_URN = 'urn:ietf:params:xml:ns:rgp-1.0';
        my $extension = $update->getNode('extension');
        $extension = $update->getNode('command')->addNewChild(undef, 'extension') if not defined $extension;
        my $rgp_update = $extension->addNewChild($RGP_URN, 'rgp:update');
        my $rgp_restore = $update->createElement('rgp:restore');
        $rgp_restore->setAttribute('op', 'request');
        $rgp_update->appendChild($rgp_restore);
    }
    if (exists $args->{rgp_restore_report}) {
        my $RGP_URN = 'urn:ietf:params:xml:ns:rgp-1.0';
        my $extension = $update->getNode('extension');
        $extension = $update->getNode('command')->addNewChild(undef, 'extension') if not defined $extension;
        my $rgp_update = $extension->addNewChild($RGP_URN, 'rgp:update');
        my $rgp_restore = $update->createElement('rgp:restore');
        $rgp_restore->setAttribute('op', 'report');
        my $rgp_report = $update->createElement('rgp:report');
        $rgp_restore->appendChild($rgp_report);
        my $report_data = $args->{rgp_restore_report};
        if (exists $report_data->{pre_data}) {
            my $report_item = $update->createElement('rgp:preData');
            $report_item->appendText($report_data->{pre_data});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{post_data}) {
            my $report_item = $update->createElement('rgp:postData');
            $report_item->appendText($report_data->{post_data});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{del_time}) {
            my $report_item = $update->createElement('rgp:delTime');
            $report_item->appendText($report_data->{del_time});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{res_time}) {
            my $report_item = $update->createElement('rgp:resTime');
            $report_item->appendText($report_data->{res_time});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{res_reason}) {
            my $report_item = $update->createElement('rgp:resReason');
            $report_item->appendText($report_data->{res_reason});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{statement1}) {
            my $report_item = $update->createElement('rgp:statement');
            $report_item->appendText($report_data->{statement1});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{statement2}) {
            my $report_item = $update->createElement('rgp:statement');
            $report_item->appendText($report_data->{statement2});
            $rgp_report->appendChild($report_item);
        }
        if (exists $report_data->{other}) {
            my $report_item = $update->createElement('rgp:other');
            $report_item->appendText($report_data->{other});
            $rgp_report->appendChild($report_item);
        }
        $rgp_update->appendChild($rgp_restore);
    }
    return $update;
}


sub cmd_domain_renew {
    my $args = shift;
    my $renew = Net::EPP::Frame::Command::Renew::Domain->new;
    $renew->clTRID->appendText(make_clTRID());
    $renew->setDomain($args->{name});
    $renew->setCurExpDate($args->{cur_exp_date});
    my $period = $renew->createElement('domain:period');
    $period->setAttribute('unit', $args->{period_units});
    $period->appendText($args->{period});
    $renew->getNode('renew')->getChildNodes->shift->appendChild($period);
    return $renew;
}


sub cmd_domain_transfer {
    my $args = shift;
    my $transfer = Net::EPP::Frame::Command::Transfer::Domain->new;
    $transfer->clTRID->appendText(make_clTRID());
    $transfer->setDomain($args->{name});
    $transfer->setOp($args->{op});
    if (exists $args->{auth_info}) {
        $transfer->setAuthInfo($args->{auth_info});
    }
    if (exists $args->{period_years}) {
        $transfer->setPeriod($args->{period_years});
    }
    return $transfer;
}


sub cmd_contact_check {
    my $args = shift;
    my $check = Net::EPP::Frame::Command::Check::Contact->new;
    $check->clTRID->appendText(make_clTRID());
    foreach my $contact (@{$args->{contacts}}) {
        $check->addContact($contact);
    }
    return $check;
}


sub cmd_contact_info {
    my $args = shift;
    my $info = Net::EPP::Frame::Command::Info::Contact->new;
    $info->clTRID->appendText(make_clTRID());
    $info->setContact($args->{contact});
    return $info;
}


sub cmd_contact_create {
    my $args = shift;
    my $create = Net::EPP::Frame::Command::Create::Contact->new;
    $create->clTRID->appendText(make_clTRID());
    $create->setContact($args->{id});
    if (exists $args->{voice}) {
        $create->setVoice($args->{voice});
    }
    if (exists $args->{fax}) {
        $create->setFax($args->{fax});
    }
    if (exists $args->{email}) {
        $create->setEmail($args->{email});
    }
    if (exists $args->{auth_info}) {
        $create->setAuthInfo($args->{auth_info});
    }
    foreach my $contact (@{$args->{contacts}}) {
        $create->addPostalInfo(
            $contact->{type}, $contact->{name}, $contact->{org}, $contact->{address},
        );
    }
    return $create;
}


sub cmd_contact_update {
    my $args = shift;
    my $update = Net::EPP::Frame::Command::Update::Contact->new;
    $update->clTRID->appendText(make_clTRID());
    $update->setContact($args->{id});
    foreach my $contact (@{$args->{contacts}}) {
        $update->chgPostalInfo(
            $contact->{type}, $contact->{name}, $contact->{org}, $contact->{address},
        );
    }
    if (exists $args->{auth_info}) {
        $update->chgAuthInfo($args->{auth_info});
    }
    if (exists $args->{voice}) {
        my $el = $update->createElement('contact:voice');
        $el->appendText($args->{voice});
        $update->getElementsByLocalName('contact:chg')->shift->appendChild($el);
    }
    if (exists $args->{fax}) {
        my $el = $update->createElement('contact:fax');
        $el->appendText($args->{fax});
        $update->getElementsByLocalName('contact:chg')->shift->appendChild($el);
    }
    if (exists $args->{email}) {
        my $el = $update->createElement('contact:email');
        $el->appendText($args->{email});
        $update->getElementsByLocalName('contact:chg')->shift->appendChild($el);
    }
    if ($args->{add_status}) {
        $update->addStatus($args->{add_status})
    } else {
        $update->add()->unbindNode();
    }
    if ($args->{rem_status}) {
        $update->remStatus($args->{rem_status})
    } else {
        $update->rem()->unbindNode();
    }
    return $update;
}


sub cmd_contact_delete {
    my $args = shift;
    my $info = Net::EPP::Frame::Command::Delete::Contact->new;
    $info->clTRID->appendText(make_clTRID());
    $info->setContact($args->{contact});
    return $info;
}


sub cmd_host_check {
    my $args = shift;
    my $check = Net::EPP::Frame::Command::Check::Host->new;
    $check->clTRID->appendText(make_clTRID());
    foreach my $host (@{$args->{hosts}}){
        $check->addHost($host);
    }
    return $check;
}


sub cmd_host_create {
    my $args = shift;
    my $create = Net::EPP::Frame::Command::Create::Host->new;
    $create->clTRID->appendText(make_clTRID());
    $create->setHost($args->{name});
    foreach my $addr (@{$args->{ip_address}}) {
        $create->setAddr($addr);
    }
    return $create;
}


sub process_request {
    my $err;
    my $resp;

    try {
        my $jsrc = shift;
        my $j = decode_json $jsrc;

        my $c = $j->{cmd};
        my $args = $j->{args};
        my $req = "";
        my $action = 'cmd_' . $c;

        {
            no strict 'refs';
            $req = $action->($args);
        }

        lll('Action: ' . $action . ' args: ' . $jsrc);

        if ( !( $action eq 'cmd_poll_req' || $action eq 'cmd_poll_ack')) {
            lll('Request: ' . Dumper($req->toString(2)));
        }
        # else { lll('Request: ' . Dumper($req->toString(2))); }

        try {
            $resp = $epp->request($req);
        } catch ($err) {
            lll('REQUEST ERROR: ' . $err);
            if (index($err, 'Got a bad frame length from peer') != -1) {
                lll("Found connection closed state! Creating new connection and RELOGIN!");
                make_client();
                hello();
                login();
                lll('Sending same Request again: ' . Dumper($req->toString(2)));
                $resp = $epp->request($req);
            }
        }

        try {
            my $result = ($resp->getElementsByTagName('result'))[0];
            if ($result->getAttribute('code') == 2002) {
                lll('Response: ' . Dumper($resp->toString(2)));
                lll("Found 2002 code in the response, RELOGIN now!");
                hello();
                login();
                lll('Sending same Request again: ' . Dumper($req->toString(2)));
                $resp = $epp->request($req);
            }
        }
        catch ($err) {
            lll('ERROR: ' . $err);
            return "";
        }

        if ( !( $action eq 'cmd_poll_req' || $action eq 'cmd_poll_ack')) {
            lll('Response: ' . Dumper($resp->toString(2)));
        }
        # else { lll('Response: ' . Dumper($resp->toString(2))); }

        if ( !( $action eq 'cmd_poll_req' || $action eq 'cmd_poll_ack')) {
            lll('============================================================');
        }

        return $resp->toString(2);
    }
    catch ($err) {
        lll('ERROR: ' . $err);
        return "";
    }
}


sub on_request {
    my $var = shift;
    my $body = $var->{body}->{payload};
    my $props = $var->{header};

    my $response = process_request($body);

    $channel->publish(
        exchange => '',
        routing_key => $props->{reply_to},
        header => {
            correlation_id => $props->{correlation_id},
        },
        body => $response,
    );

    $channel->ack();
}


sub server {
    my $rabbitmq_credentials_file = $ARGV[1];
    open (my $inFile, '<', $rabbitmq_credentials_file) or die "$rabbitmq_credentials_file";
    my $firstLine = <$inFile>;
    close $inFile;
    my ($rabbitmq_host, $rabbitmq_port, $rabbitmq_username, $rabbitmq_password) = split / /, $firstLine;
    $rabbitmq_host =~ s/^\s+|\s+$//g;
    $rabbitmq_port =~ s/^\s+|\s+$//g;
    $rabbitmq_username =~ s/^\s+|\s+$//g;
    $rabbitmq_password =~ s/^\s+|\s+$//g;

    lll("Connecting to RabbitMQ server at " . $rabbitmq_host . ":" . $rabbitmq_port . " with username: " . $rabbitmq_username);

    $conn = Net::RabbitFoot->new()->load_xml_spec()->connect(
        host => $rabbitmq_host,
        port => $rabbitmq_port,
        user => $rabbitmq_username,
        pass => $rabbitmq_password,
        vhost => '/',
    );

    $channel = $conn->open_channel();

    $channel->declare_queue(queue => 'epp_messages');
    $channel->qos(prefetch_count => 1);
    $channel->consume(
        on_consume => \&on_request,
    );

    lll(" [x] Awaiting RPC requests\n");

    # Wait forever
    AnyEvent->condvar->recv;
}


make_client();

server();
