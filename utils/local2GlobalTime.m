function [global_sample_timestamps_usec] = local2GlobalTime(local_ttl_ts_us, local_sample_ts_us, varargin)
%local2GlobalTime Interpolates global timestamps 
%   Uses intepolation to calculate sample timestamps relative to global
%   clock (Master9 / TTL source)
%   ----------
%   Parameters
%   ----------
%   local_ttl_ts_us
%       Timestamps in usec of TTLs as recorded on local device
%   local_sample_ts_us
%       Timestamps in usec of sample points in local data
%   (Name, Value) 'global_ttl_interval_usec'
%       Ground truth (by definition) interval between TTLs in usec. 
%       Defaults to 3 sec (3e6 usec). 
%     OR
%   (Name, Value) 'custom_global_ttl_ts_us'
%       Custom ground truth ttl definition (Use this for non-uniformly
%       spaced TTLs). Overrides global_ttl_interval_usec.
%   ----------
%   Outputs
%   ----------
%   global_sample_timestamps_usec
%       Timestamps in usec of each data sample in global time (relative to
%       ground truth clock)
%   ----------
%   Principle
%   ----------
%   t_i = local timestamps of TTLs
%   T_i = global timestamps of TTLs (ground truth, as defined on Master9).
%   The function F(t_i) = T_i maps local timestamps to global timestamps.
%   This function is sampled at each TTL. Thus in order to obtain the
%   timestamps of data samples occuring between TTL, we can use linear
%   interpolation to obtain F(t). We can then sample F at any local time points we
%   wish and obtain the corresponding global time stamps.

defaultTTLInterval = 3e6; % 3 sec TTL

% -------------------------- Input parser --------------------------
p = inputParser;
addRequired(p,'local_ttl_ts_us');
addRequired(p,'local_sample_ts_us');
addOptional(p,'global_ttl_interval_us',defaultTTLInterval);
addOptional(p,'custom_global_ttl_ts_us',0);
parse(p,local_ttl_ts_us,local_sample_ts_us,varargin{:});

global_ttl_interval_us = p.Results.global_ttl_interval_us;
custom_global_ttl_ts_us = p.Results.custom_global_ttl_ts_us;
% ------------------------------------------------------------------



% ------------------------- Interpolation -------------------------
num_ttl = length(local_ttl_ts_us); % Total number of TTLs
local_ttl_t0 = local_ttl_ts_us(1); % First local TTL timestamp in usec
if(custom_global_ttl_ts_us == 0) % If no custom global TTL defined
    % Global ttl ts (ground truth) as defined by global ttl spacing
    global_ttl_ts_us = linspace(round(local_ttl_t0), round(local_ttl_t0 + (num_ttl-1)*global_ttl_interval_us), num_ttl);
else % Use custom global TTL timestamps
    global_ttl_ts_us = custom_global_ttl_ts_us;
end

%disp(diff(global_ttl_ts_us));

% Perform interpolation and sample desired timestamps
global_sample_ts_us = interp1(local_ttl_ts_us,global_ttl_ts_us,local_sample_ts_us,'linear','extrap');

global_sample_timestamps_usec = global_sample_ts_us;
global_sample_timestamps_usec = global_sample_timestamps_usec - global_ttl_ts_us(1);
% ------------------------------------------------------------------

close all


% Plot interpolation results
figure;
scatter(local_ttl_ts_us,global_ttl_ts_us,30,'MarkerEdgeColor','red', 'MarkerEdgeAlpha',0.2)
hold on
plot(local_sample_ts_us,global_sample_ts_us, 'LineWidth', 2, 'Color','blue')
title('Interpolation')
xlabel('Local TTL timestamps (usec)');
ylabel('Global timestamps (usec)')
axis equal;

end