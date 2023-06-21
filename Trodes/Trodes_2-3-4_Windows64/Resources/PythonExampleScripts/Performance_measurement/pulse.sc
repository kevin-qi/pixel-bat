int a = 1




%here we define a function that can be executed with the "trigger" command
%every function is defined by a number
function 1
	
	portout[1] = 1
	do in 1
		portout[1] = 0
	end

end

function 2
	while a==1 do every 1000
		
		portout[2] = 1
		do in 1
			portout[2] = 0
		end
	end
end



trigger(2);





