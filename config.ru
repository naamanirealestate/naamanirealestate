require "rack/static"
use Rack::Static, urls: ["/images", "/css", "/js"], root: "."

run lambda { |env|
  [200, { "content-type" => "text/html", "cache-control" => "public, max-age=86400" }, File.open("index.html", File::RDONLY)]
}
