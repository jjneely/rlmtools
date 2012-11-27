# a config.ru, for use with every rack-compatible webserver.
# SSL needs to be handled outside this, though.

# Set the SHELL PATH.  We used to work without this, now suddenly
# things blow up badly without setting the PATH
ENV['PATH'] = "/bin:/usr/bin:/sbin:/usr/sbin"

# if puppet is not in your RUBYLIB:
# $:.unshift('/opt/puppet/lib')

$0 = "master"

# if you want debugging:
# ARGV << "--debug"

ARGV << "--rack"
require 'puppet/application/master'

class AuthZWrapper

  def initialize(app)
    @app = app
    @cache = {}
  end

  def getDept(uuid)
    epoch = Time.now.to_i()
    if @cache.has_key?(uuid) and @cache[uuid][0] > epoch - 120
        # cache hit
        return @cache[uuid][1]
    else
        # cache miss
        dept = %x{/usr/bin/python /etc/puppet/getdept.py #{uuid}}
        if $? != 0
            return Nil
        end
        # Normalize dept string to match puppet environments
        dept.tr!("-", "_")
        @cache[uuid] = [epoch, dept]
        return dept
    end
  end

  def call(env)
    hostname = ""
    uuid = ""
    dept = ""
    environment = ""

    # Get the Puppet Environment
    if env['REQUEST_URI'] =~ /\/([^\/]+).*/
        environment = $1
    end

    # Make sure Environments exist and return a sane error code if not
    if environment != "" and not File.directory?("/srv/puppet/#{environment}")
        # This environment doesn't exist, tell the client
        return [404, "", "Environment \"#{environment}\" not found"]
    end

    # Let Puppet deal with non-verified clients and URI issues
    if environment != "" and env['HTTP_X_CLIENT_VERIFY'] == "SUCCESS"
        if env['HTTP_X_CLIENT_DN'] =~ /\/CN=([-_a-zA-Z0-9.]+)-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/
            hostname = $1
            uuid = $2
            dept = self.getDept(uuid)
            if dept.nil?
                return [500, "", "Error determining department for #{uuid}"]
            end

            # Now make sure this dept can read this enivornment.  Some
            # departments/environments are world read.
            if environment =~ /^root$|^ncsu$|^test|^production$|^#{dept}/
                return @app.call(env)
            else
                return [403, "", "Host #{uuid} from department #{dept.tr("_", "-")} may not access Puppet Environment #{environment}"]
            end
        end
    else
        status, headers, body = @app.call(env)
        [status, headers, body]
    end
  end
end

use AuthZWrapper

# we're usually running inside a Rack::Builder.new {} block,
# therefore we need to call run *here*.
run Puppet::Application[:master].run
