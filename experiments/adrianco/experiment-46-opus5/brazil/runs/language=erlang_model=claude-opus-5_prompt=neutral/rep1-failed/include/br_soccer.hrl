%%%-------------------------------------------------------------------
%%% Shared record definitions for the Brazilian soccer knowledge graph.
%%%-------------------------------------------------------------------
-ifndef(BR_SOCCER_HRL).
-define(BR_SOCCER_HRL, true).

%% A single match, normalised across all five match data sets.
-record(match, {
          id                  :: binary(),            % deterministic dedupe key
          sources = []        :: [atom()],            % data sets the match came from
          competition         :: binary(),            % canonical competition id
          season              :: integer() | undefined,
          date                :: calendar:date() | undefined,
          time                :: calendar:time() | undefined,
          round               :: binary() | undefined,
          stage               :: binary() | undefined,
          home                :: binary(),            % canonical team id
          away                :: binary(),            % canonical team id
          home_name           :: binary(),            % display name as found in source
          away_name           :: binary(),
          home_goals          :: integer() | undefined,
          away_goals          :: integer() | undefined,
          venue               :: binary() | undefined,
          stats = #{}         :: map()                % corners/shots/attacks when available
         }).

%% A team/club node of the knowledge graph.
-record(team, {
          id                  :: binary(),
          name                :: binary(),            % display name
          state               :: binary() | undefined,% Brazilian federal unit (UF)
          country             :: binary() | undefined,
          aliases = []        :: [binary()],          % spellings seen in the data
          match_count = 0     :: non_neg_integer(),
          competitions = []   :: [binary()],
          seasons = []        :: [integer()]
         }).

%% A player from the FIFA data set.
-record(player, {
          id                  :: integer(),
          name                :: binary(),
          norm_name           :: binary(),
          age                 :: integer() | undefined,
          nationality         :: binary() | undefined,
          overall             :: integer() | undefined,
          potential           :: integer() | undefined,
          club                :: binary() | undefined,% display name from source
          club_id             :: binary() | undefined,% canonical team id
          position            :: binary() | undefined,
          jersey              :: integer() | undefined,
          height              :: binary() | undefined,
          weight              :: binary() | undefined,
          value               :: binary() | undefined,
          wage                :: binary() | undefined,
          foot                :: binary() | undefined,
          skills = #{}        :: map()
         }).

-endif.
