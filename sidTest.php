<?
	include_once("inc.connect.php");
	include_once("inc.functions.php");
	
	function Pv($n){
		if( array_key_exists($n,$_POST) ) return $_POST[$n]; else return "";
	}
	
	$mac = $_GET['mac'];
	$mac = strtolower(str_replace(":","",$mac));
	$mac = "0x".$mac."L";
	
	$dbid = SV("select `id` from `cameras` where `macaddress` like '$mac'");
//echo "select `id` from `cameras` where `macaddress` like '$mac'";
	$id1 = 10000+$dbid;
	$id2 = 20000+$dbid;

//	$tserver = "34.220.247.80";
//	$cert = "TDTCert.pem";

	$tserver = "microvs.com";
	$cert = "RPWebServer.pem";
		
	
	echo "#! /bin/bash\n";
	echo "createTunnel() {\n";
	echo "    /usr/bin/ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -f -N -R ".$id1.":localhost:22 -L ".$id2.":".$tserver.":22 -i '$cert' ubuntu@".$tserver."\n";
	echo "    if [[ $? -eq 0 ]]; then\n";
	echo "        echo Tunnel to Server created successfully\n";
	echo "    else\n";
	echo "        echo An error occurred creating a tunnel to Server. Return code: $?\n";
	echo "    fi\n";
	echo "}\n";
	echo "/usr/bin/ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p ".$id2." -i '$cert' ubuntu@localhost ls > /dev/null\n";
	echo "if [[ $? -ne 0 ]]; then\n";
	echo "    echo Creating new tunnel connection to Server\n";
	echo "    createTunnel\n";
  echo "    sudo sed -i 's/\r$//' /var/spool/cron/crontabs/pi\n";
	echo "fi\n";

	/*


	ifconfig eth0 | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}'


	a=(`ps -ef | egrep 'startx' | grep -v grep`)
	if [ ${#a} == 0 ]; then
	  /home/pi/Desktop/CamManager/do_update.sh
	  /home/pi/Desktop/CamManager/start.sh
	fi

	*/
